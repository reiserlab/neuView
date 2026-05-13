"""
Neuron Type Discovery

Resolves the canonical set of neuron types from the cache/queue and the
database. Both ``IndexService`` and ``ScatterplotService`` need this
resolution step, so it lives here as a small shared helper rather than
on either service.
"""

import logging
import time
from collections import defaultdict
from pathlib import Path

from .neuron_name_service import NeuronNameService
from .roi_hierarchy_service import ROIHierarchyService

logger = logging.getLogger(__name__)


class NeuronTypeDiscovery:
    """Discover neuron types and resolve their canonical names.

    Collaborates with the cache manager and (when needed) a NeuPrint
    connector. ``roi_hierarchy_service`` and ``neuron_name_service``
    can be passed in to share state with another service (e.g.
    ``IndexService`` reuses its ROI hierarchy cache); otherwise this
    class creates its own.
    """

    def __init__(
        self,
        config,
        cache_manager,
        *,
        roi_hierarchy_service=None,
        neuron_name_service=None,
    ):
        self.config = config
        self.cache_manager = cache_manager
        self.roi_hierarchy_service = roi_hierarchy_service or ROIHierarchyService(
            config, cache_manager
        )
        self.neuron_name_service = neuron_name_service or NeuronNameService(
            cache_manager
        )

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
