"""
Index Service

Simplified service that coordinates other specialized services to create
index pages that list all available neuron types.
"""

import logging
import time
from pathlib import Path
from collections import defaultdict

from ..result import Result, Ok, Err
from ..utils import get_git_version
from .roi_hierarchy_service import ROIHierarchyService
from .neuron_name_service import NeuronNameService
from .roi_analysis_service import ROIAnalysisService
from .index_generator_service import IndexGeneratorService
from .file_service import FileService

logger = logging.getLogger(__name__)


class IndexService:
    """Service for creating index pages that list all available neuron types."""

    def __init__(self, config, page_generator):
        self.config = config
        self.page_generator = page_generator
        self._batch_neuron_cache = {}

        # Initialize cache manager for neuron type data
        self.cache_manager = None
        if config and hasattr(config, "output") and hasattr(config.output, "directory"):
            from ..cache import create_cache_manager

            self.cache_manager = create_cache_manager(config.output.directory)

        # Initialize specialized services
        self.roi_hierarchy_service = ROIHierarchyService(config, self.cache_manager)
        self.neuron_name_service = NeuronNameService(self.cache_manager)
        self.roi_analysis_service = ROIAnalysisService(
            page_generator, self.roi_hierarchy_service
        )
        self.index_generator_service = IndexGeneratorService(page_generator)

    async def create_index(self, command) -> Result[str, str]:
        """Create an index page listing all neuron types found in the output directory."""
        try:
            logger.info("Starting index creation using cached data")
            start_time = time.time()

            # Determine output directory
            output_dir = Path(command.output_directory or self.config.output.directory)
            if not output_dir.exists():
                return Err(f"Output directory does not exist: {output_dir}")

            # Discover neuron types from cache or file scanning
            neuron_types, scan_time = self.discover_neuron_types(output_dir)
            if not neuron_types:
                return Err("No neuron type HTML files found in output directory")

            # Initialize connector if needed for database lookups
            connector = await self.initialize_connector_if_needed(
                neuron_types, output_dir
            )

            # Correct neuron names (convert filenames back to original names)
            corrected_neuron_types, cache_performance = self.correct_neuron_names(
                neuron_types, connector
            )

            # Generate index data from corrected neuron types
            index_data = self._generate_index_data(corrected_neuron_types)

            # Log performance summary
            self._log_performance_summary(
                corrected_neuron_types, cache_performance, scan_time
            )

            # Generate all the pages and files
            await self._generate_all_pages(output_dir, index_data, command, connector)

            total_time = time.time() - start_time
            logger.info(f"Total optimized index creation: {total_time:.3f}s")

            # Collect all generated file paths
            generated_files = [str(output_dir / command.index_filename)]
            if hasattr(self, "generated_files"):
                generated_files.extend(self.generated_files)

            return Ok(generated_files)

        except Exception as e:
            logger.error(f"Failed to create optimized index: {e}")
            return Err(f"Failed to create index: {str(e)}")

    def discover_neuron_types(self, output_dir: Path) -> tuple:
        """Discover neuron types from queue file to ensure all are included."""
        neuron_types = defaultdict(set)

        # Load neuron types from cache manifest file for completeness
        try:
            import json

            with open(output_dir / ".cache" / "manifest.json", "r") as f:
                manifest_data = json.load(f)
            cached_neurons = manifest_data.get("neuron_types", [])
            logger.info(
                f"Loading {len(cached_neurons)} neuron types from cache manifest file"
            )

            # Get cached data for metadata
            cached_data_lazy = None
            if self.cache_manager:
                cached_data_lazy = self.cache_manager.get_cached_data_lazy()
                logger.info(
                    f"Found cached data for {len(cached_data_lazy)} neuron types"
                )

            # Process each neuron type from cache manifest
            cache_hits = 0
            for neuron_type in cached_neurons:
                # Check cache for soma side information
                cache_data = None
                if cached_data_lazy:
                    # Try original name first, then try sanitized variations
                    cache_data = cached_data_lazy.get(neuron_type)
                    if not cache_data:
                        # Try common sanitizations
                        sanitized_variants = [
                            neuron_type.replace(" ", ""),
                            neuron_type.replace(", ", ""),
                            neuron_type.replace(" ", "").replace(",", ""),
                            neuron_type.replace("/", "").replace(" ", ""),
                            neuron_type.replace("'", "").replace(" ", ""),
                            neuron_type.replace("&", "").replace(" ", ""),
                            neuron_type.replace(".", "").replace(" ", ""),
                            neuron_type.replace("(", "")
                            .replace(")", "")
                            .replace(" ", ""),
                        ]
                        for variant in sanitized_variants:
                            cache_data = cached_data_lazy.get(variant)
                            if cache_data:
                                logger.debug(
                                    f"Found cache data for '{neuron_type}' via variant '{variant}'"
                                )
                                break

                if cache_data:
                    cache_hits += 1
                    # Use cache data for soma sides
                    if not cache_data.soma_sides_available:
                        neuron_types[neuron_type].add("combined")
                    else:
                        for side in cache_data.soma_sides_available:
                            if side == "combined":
                                neuron_types[neuron_type].add("combined")
                            elif side == "left":
                                neuron_types[neuron_type].add("L")
                            elif side == "right":
                                neuron_types[neuron_type].add("R")
                            elif side == "middle":
                                neuron_types[neuron_type].add("M")
                else:
                    # No cache data - use default
                    neuron_types[neuron_type].add("combined")
                    logger.debug(f"No cache data for '{neuron_type}', using default")

            logger.info(
                f"Queue-based discovery completed: {len(neuron_types)} total, {cache_hits} with cache data"
            )
            return neuron_types, 0.0

        except Exception as e:
            logger.warning(
                f"Could not load queue file, falling back to cache discovery: {e}"
            )
            # Fallback to original cache-based discovery
            cached_data_lazy = None
            if self.cache_manager:
                cached_data_lazy = self.cache_manager.get_cached_data_lazy()

            if cached_data_lazy and len(cached_data_lazy) > 0:
                logger.info(
                    f"Using cached data for {len(cached_data_lazy)} neuron types (fallback mode)"
                )
                for neuron_type in cached_data_lazy.keys():
                    cache_data = cached_data_lazy.get(neuron_type)
                    if cache_data:
                        if not cache_data.soma_sides_available:
                            neuron_types[neuron_type].add("combined")
                        else:
                            for side in cache_data.soma_sides_available:
                                if side == "combined":
                                    neuron_types[neuron_type].add("combined")
                                elif side == "left":
                                    neuron_types[neuron_type].add("L")
                                elif side == "right":
                                    neuron_types[neuron_type].add("R")
                                elif side == "middle":
                                    neuron_types[neuron_type].add("M")
                return neuron_types, 0.0
            else:
                # No cache data available - return empty
                logger.error(
                    "No queue file or cache data available for neuron type discovery"
                )
                return neuron_types, 0.0

    async def initialize_connector_if_needed(self, neuron_types, output_dir):
        """Initialize database connector only if needed for lookups."""
        # Pre-load ROI hierarchy from cache (no database queries if cached)
        roi_hierarchy_loaded = False
        if self.cache_manager:
            hierarchy = self.cache_manager.load_roi_hierarchy()
            if hierarchy:
                self.roi_hierarchy_service._roi_hierarchy_cache = hierarchy
                logger.info(
                    "Loaded ROI hierarchy from cache - no database queries needed"
                )
                roi_hierarchy_loaded = True

        # Check if we need neuron name correction
        cached_data_lazy = (
            self.cache_manager.get_cached_data_lazy() if self.cache_manager else None
        )
        names_needing_db_lookup = []

        if not cached_data_lazy or len(cached_data_lazy) == 0:
            # We'll need to convert filenames to neuron names
            filename_to_neuron_map = (
                self.neuron_name_service.build_filename_to_neuron_map(cached_data_lazy)
            )
            for filename_based_name in neuron_types.keys():
                if filename_based_name not in filename_to_neuron_map:
                    names_needing_db_lookup.append(filename_based_name)

        # Only initialize connector if we need database lookups or metadata retrieval
        connector = None
        if names_needing_db_lookup or not roi_hierarchy_loaded:
            try:
                init_start = time.time()
                from ..neuprint_connector import NeuPrintConnector

                connector = NeuPrintConnector(self.config)

                # Load ROI hierarchy if not already cached
                if not roi_hierarchy_loaded:
                    self.roi_hierarchy_service.get_roi_hierarchy_cached(
                        connector, output_dir
                    )
                    logger.warning(
                        "ROI hierarchy not found in cache, had to fetch from database"
                    )

                init_time = time.time() - init_start
                logger.info(f"Database connector initialized in {init_time:.3f}s")

            except Exception as e:
                logger.warning(f"Failed to initialize connector: {e}")
        else:
            # Even if we don't need database lookups for names or ROI hierarchy,
            # we still need the connector for metadata retrieval (UUID, etc.)
            try:
                init_start = time.time()
                from ..neuprint_connector import NeuPrintConnector

                connector = NeuPrintConnector(self.config)
                init_time = time.time() - init_start
                logger.info(
                    f"Database connector initialized for metadata retrieval in {init_time:.3f}s"
                )

            except Exception as e:
                logger.warning(f"Failed to initialize connector for metadata: {e}")

        return connector

    def correct_neuron_names(self, neuron_types, connector):
        """Correct neuron names by converting filenames back to original names."""
        cached_data_lazy = (
            self.cache_manager.get_cached_data_lazy() if self.cache_manager else None
        )

        if cached_data_lazy and len(cached_data_lazy) > 0:
            # Fast mode: neuron_types already contains correct neuron names from cache
            logger.info(
                "Using cached neuron names directly - no filename conversion needed"
            )
            return dict(neuron_types), {
                "cache_hits": len(neuron_types),
                "db_lookups": 0,
            }

        # Scan mode: neuron_types contains filenames that need to be converted to neuron names
        logger.info("Converting filenames to neuron names using cache/database lookup")
        corrected_neuron_types = {}
        names_needing_db_lookup = []
        neuron_name_cache_hits = 0

        # Build reverse lookup map for efficient filename-to-neuron-name mapping
        filename_to_neuron_map = self.neuron_name_service.build_filename_to_neuron_map(
            cached_data_lazy
        )

        for filename_based_name, sides in neuron_types.items():
            # Try to get correct name from cache first
            if filename_based_name in filename_to_neuron_map:
                original_name = filename_to_neuron_map[filename_based_name]
                corrected_neuron_types[original_name] = sides
                logger.debug(
                    f"Found original neuron name from cache: {filename_based_name} -> {original_name}"
                )
                neuron_name_cache_hits += 1
            else:
                # Need database lookup for this name
                names_needing_db_lookup.append((filename_based_name, sides))

        # Handle names that need database lookup
        if names_needing_db_lookup and connector:
            logger.warning(
                f"Cache miss for {len(names_needing_db_lookup)} neuron name(s), using database lookup"
            )
            for filename_based_name, sides in names_needing_db_lookup:
                correct_name = self.neuron_name_service.filename_to_neuron_name(
                    filename_based_name, connector
                )
                corrected_neuron_types[correct_name] = sides
        elif names_needing_db_lookup:
            # Use original names as fallback
            for filename_based_name, sides in names_needing_db_lookup:
                corrected_neuron_types[filename_based_name] = sides

        return corrected_neuron_types, {
            "cache_hits": neuron_name_cache_hits,
            "db_lookups": len(names_needing_db_lookup),
        }

    def _generate_index_data(self, neuron_types):
        """Generate index data from neuron types."""
        cached_data_lazy = (
            self.cache_manager.get_cached_data_lazy() if self.cache_manager else None
        )
        index_data = []
        cached_count = 0
        missing_cache_count = 0

        for neuron_type, sides in neuron_types.items():
            # Check if we have cached data for this neuron type
            cache_data = cached_data_lazy.get(neuron_type) if cached_data_lazy else None

            has_combined = "combined" in sides
            has_left = "L" in sides
            has_right = "R" in sides
            has_middle = "M" in sides

            entry = {
                "name": neuron_type,
                "has_combined": has_combined,
                "has_left": has_left,
                "has_right": has_right,
                "has_middle": has_middle,
                "combined_url": f"types/{FileService.generate_filename(neuron_type, 'combined')}"
                if has_combined
                else None,
                "left_url": f"types/{FileService.generate_filename(neuron_type, 'left')}"
                if has_left
                else None,
                "right_url": f"types/{FileService.generate_filename(neuron_type, 'right')}"
                if has_right
                else None,
                "middle_url": f"types/{FileService.generate_filename(neuron_type, 'middle')}"
                if has_middle
                else None,
                "roi_summary": [],
                "parent_roi": "",
                "parent_rois": [],
                "total_count": 0,
                "left_count": 0,
                "right_count": 0,
                "middle_count": 0,
                "undefined_count": 0,
                "has_undefined": False,
                "consensus_nt": None,
                "celltype_predicted_nt": None,
                "celltype_predicted_nt_confidence": None,
                "celltype_total_nt_predictions": None,
                "cell_class": None,
                "cell_subclass": None,
                "cell_superclass": None,
                "dimorphism": None,
                "synonyms": None,
                "flywire_types": None,
                "soma_neuromere": None,
                "truman_hl": None,
                "processed_synonyms": {},
                "processed_flywire_types": {},
            }

            # Use cached data if available (NO DATABASE QUERIES!)
            if cache_data:
                entry["roi_summary"] = cache_data.roi_summary
                # Handle parent_rois list and maintain backward compatibility with parent_roi
                parent_rois = getattr(cache_data, "parent_rois", [])

                # Migration fallback: handle old cache data with parent_roi instead of parent_rois
                if (
                    not parent_rois
                    and hasattr(cache_data, "parent_roi")
                    and cache_data.parent_roi
                ):
                    parent_rois = [cache_data.parent_roi]
                    logger.debug(
                        f"Migrating old cache format for {neuron_type}: parent_roi='{cache_data.parent_roi}' -> parent_rois={parent_rois}"
                    )

                if parent_rois:
                    # Clean parent ROI names by removing side suffixes for display
                    cleaned_parent_rois = [
                        self.roi_hierarchy_service._clean_roi_name(roi)
                        for roi in parent_rois
                    ]
                    entry["parent_rois"] = [roi for roi in cleaned_parent_rois if roi]
                    # For backward compatibility, use first parent ROI as parent_roi
                    entry["parent_roi"] = (
                        entry["parent_rois"][0] if entry["parent_rois"] else ""
                    )
                else:
                    entry["parent_rois"] = []
                    entry["parent_roi"] = ""
                entry["total_count"] = cache_data.total_count
                entry["left_count"] = cache_data.soma_side_counts.get("left", 0)
                entry["right_count"] = cache_data.soma_side_counts.get("right", 0)
                entry["middle_count"] = cache_data.soma_side_counts.get("middle", 0)
                entry["undefined_count"] = cache_data.soma_side_counts.get("unknown", 0)
                entry["has_undefined"] = entry["undefined_count"] > 0
                entry["consensus_nt"] = cache_data.consensus_nt
                entry["celltype_predicted_nt"] = cache_data.celltype_predicted_nt
                entry["celltype_predicted_nt_confidence"] = (
                    cache_data.celltype_predicted_nt_confidence
                )
                entry["celltype_total_nt_predictions"] = (
                    cache_data.celltype_total_nt_predictions
                )
                entry["cell_class"] = cache_data.cell_class
                entry["cell_subclass"] = cache_data.cell_subclass
                entry["cell_superclass"] = cache_data.cell_superclass
                entry["dimorphism"] = cache_data.dimorphism
                entry["synonyms"] = cache_data.synonyms
                entry["flywire_types"] = cache_data.flywire_types
                entry["soma_neuromere"] = cache_data.soma_neuromere
                entry["truman_hl"] = cache_data.truman_hl

                # Process synonyms and flywire types for structured template rendering
                if cache_data.synonyms:
                    entry["processed_synonyms"] = (
                        self.page_generator.text_utils.process_synonyms(
                            cache_data.synonyms,
                            self.page_generator.citations,
                            neuron_type,
                            str(self.page_generator.output_dir),
                        )
                    )
                if cache_data.flywire_types:
                    entry["processed_flywire_types"] = (
                        self.page_generator.text_utils.process_flywire_types(
                            cache_data.flywire_types, neuron_type
                        )
                    )
                logger.debug(f"Used cached data for {neuron_type}")
                cached_count += 1
            else:
                # No cached data available - use minimal defaults
                logger.debug(
                    f"No cached data available for {neuron_type}, using minimal defaults"
                )
                missing_cache_count += 1

            index_data.append(entry)

        # Sort results
        index_data.sort(key=lambda x: x["name"])

        if missing_cache_count > 0:
            logger.warning(
                f"Index data generation completed: {len(index_data)} entries, {cached_count} with cache, {missing_cache_count} missing cache. Run 'neuview generate' to populate cache."
            )
        else:
            logger.info(
                f"Index data generation completed: {len(index_data)} entries, all with cached data"
            )
        return index_data

    async def _generate_all_pages(self, output_dir, index_data, command, connector):
        """Generate all the index pages and associated files."""
        cached_data_lazy = (
            self.cache_manager.get_cached_data_lazy() if self.cache_manager else None
        )

        # No longer grouping by parent ROI - using flat list instead

        # Collect filter options
        filter_options = (
            self.roi_analysis_service.collect_filter_options_from_index_data(index_data)
        )
        filter_options["cell_count_ranges"] = (
            self.roi_analysis_service.calculate_cell_count_ranges(index_data)
        )

        # Calculate totals
        totals = self.index_generator_service.calculate_totals(
            index_data, cached_data_lazy
        )

        # Get database metadata
        metadata = {
            "version": "Unknown",
            "uuid": "Unknown",
            "lastDatabaseEdit": "Unknown",
        }
        if connector:
            metadata = self.index_generator_service.get_database_metadata(connector)

        # Generate the index page using Jinja2
        render_start = time.time()
        template_data = {
            "config": self.config,
            "neuron_types": index_data,  # Used for both JavaScript filtering and display
            "total_types": len(index_data),
            "total_neurons": totals["total_neurons"],
            "total_synapses": totals["total_synapses"],
            "metadata": metadata,
            "generation_time": command.requested_at,
            "git_version": get_git_version(),
            "is_neuron_page": False,
            "filter_options": filter_options,
        }

        # Use the page generator's Jinja environment
        template = self.page_generator.env.get_template("types.html.jinja")
        html_content = template.render(template_data)

        # Minify HTML content to reduce whitespace (without JS minification for index page)
        if command.minify:
            html_content = self.page_generator.html_utils.minify_html(
                html_content, minify_js=True
            )

        # Write the index file
        index_path = output_dir / command.index_filename
        index_path.write_text(html_content, encoding="utf-8")

        # Generate neuron-search.js file with discovered neuron types
        js_path = await self.index_generator_service.generate_neuron_search_js(
            output_dir, index_data, command.requested_at
        )

        # Generate README.md documentation for the website
        readme_path = await self.index_generator_service.generate_readme(
            output_dir, template_data
        )

        # Generate help.html page
        help_path = await self.index_generator_service.generate_help_page(
            output_dir, template_data, not command.minify
        )

        # Generate index.html landing page
        landing_page_path = await self.index_generator_service.generate_index_page(
            output_dir, template_data, not command.minify
        )

        # Collect all generated file paths for return
        self.generated_files = []
        if js_path:
            self.generated_files.append(js_path)
        if readme_path:
            self.generated_files.append(readme_path)
        if help_path:
            self.generated_files.append(help_path)
        if landing_page_path:
            self.generated_files.append(landing_page_path)

        render_time = time.time() - render_start
        logger.info(f"Template rendering completed in {render_time:.3f}s")

    def _log_performance_summary(self, neuron_types, cache_performance, scan_time):
        """Log comprehensive performance summary."""
        total_types = len(neuron_types)

        # Log cache usage summary
        cached_count = cache_performance.get("cache_hits", 0)
        missing_cache_count = cache_performance.get("db_lookups", 0)

        logger.info(
            f"Index creation summary: {cached_count}/{total_types} neuron types used cached data, "
            f"{missing_cache_count} types had no cache (used defaults)"
        )

        # Log comprehensive cache performance summary
        total_efficiency_score = 0
        max_efficiency_score = 3  # ROI hierarchy + neuron names + neuron data

        # ROI hierarchy efficiency
        roi_hierarchy_loaded = (
            self.roi_hierarchy_service._roi_hierarchy_cache is not None
        )
        if roi_hierarchy_loaded:
            total_efficiency_score += 1

        # Neuron name efficiency
        if missing_cache_count == 0:
            total_efficiency_score += 1

        # Neuron data efficiency
        if cached_count == total_types:
            total_efficiency_score += 1

        if total_efficiency_score == max_efficiency_score:
            logger.info(
                "✅ PERFECT: Complete cache-only index creation - no database queries performed!"
            )
        else:
            logger.info(
                f"Cache efficiency: {total_efficiency_score}/{max_efficiency_score} components cached"
            )

            if missing_cache_count > 0:
                logger.warning(
                    f"⚠️  {missing_cache_count} neuron types missing cache data - consider regenerating cache"
                )
            if cache_performance.get("db_lookups", 0) > 0:
                logger.warning(
                    f"⚠️  {cache_performance['db_lookups']} neuron names required database lookup - consider regenerating cache"
                )
            if not roi_hierarchy_loaded:
                logger.warning(
                    "⚠️  ROI hierarchy not cached - consider running generate to cache this data"
                )
