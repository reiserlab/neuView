"""
HTML page generator using Jinja2 templates.

This module provides comprehensive HTML page generation functionality for
neuron type reports, including template rendering, static file management,
and output directory organization.
"""

from pathlib import Path
import pandas as pd
import logging
from typing import Dict, Any, Optional, List

from .config import Config
from .visualization.data_transfer_objects import (
    create_grid_generation_request,
    SomaSide,
)
from .visualization.data_processing.data_adapter import DataAdapter
from .services.file_service import FileService
from .models.page_generation import PageGenerationRequest

logger = logging.getLogger(__name__)


class PageGenerator:
    """
    Generate HTML pages for neuron types.

    This class handles the complete page generation process including template
    rendering, static file copying, and output file management.
    """

    def __init__(
        self,
        config: Config,
        output_dir: str,
        queue_service=None,
        cache_manager=None,
        services=None,
        container=None,
        copy_mode: str = "check_exists",
    ):
        """
        Initialize the page generator.

        Args:
            config: Configuration object with template and output settings
            output_dir: Directory path for generated HTML files
            queue_service: Optional QueueService for checking queued neuron types
            cache_manager: Optional cache manager for accessing cached neuron data
            services: Pre-configured services dictionary (used by factory) - either this or container must be provided
            container: Dependency injection container - either this or services must be provided
            copy_mode: Static file copy mode ("check_exists" for pop, "force_all" for generate)

        Raises:
            ValueError: If neither services nor container is provided
        """
        self.config = config
        self.output_dir = Path(output_dir)

        self.queue_service = queue_service
        self._neuron_cache_manager = cache_manager
        self.copy_mode = copy_mode

        if container:
            # Use dependency injection container
            self._init_from_container(container)
        elif services:
            # Use factory-created services
            self._init_from_services(services)
        else:
            # Either services or container must be provided
            raise ValueError(
                "Either 'services' or 'container' must be provided. "
                "Use PageGenerator.create_with_factory() or PageGenerator.create_with_container() "
                "instead of direct instantiation."
            )

    def _init_from_container(self, container):
        """Initialize PageGenerator from dependency injection container."""
        self.container = container

        # Configure container services
        container.configure_data_services()
        container.configure_template_environment()
        container.configure_page_generator_services(self)

        # Extract core services
        self.brain_region_service = container.get("brain_region_service")
        self.citation_service = container.get("citation_service")
        self.partner_analysis_service = container.get("partner_analysis_service")
        self.jinja_template_service = container.get("jinja_template_service")
        self.neuron_search_service = container.get("neuron_search_service")

        # Extract core data and resources
        self.brain_regions = container.get("brain_regions")
        self.citations = container.get("citations")
        self.resource_manager = container.get("resource_manager")

        # Add new managers
        self.template_manager = container.template_manager
        self.resource_manager_v3 = container.resource_manager_v3
        self.dependency_manager = container.dependency_manager

        # Setup directories
        directories = self.resource_manager.setup_output_directories()
        self.types_dir = directories["types"]
        self.eyemaps_dir = directories["eyemaps"]
        self.eyemap_generator = container.get("hexagon_generator")

        # Extract utility classes
        self.html_utils = container.get("html_utils")
        self.text_utils = container.get("text_utils")
        self.number_formatter = container.get("number_formatter")
        self.percentage_formatter = container.get("percentage_formatter")
        self.synapse_formatter = container.get("synapse_formatter")
        self.neurotransmitter_formatter = container.get("neurotransmitter_formatter")
        self.mathematical_formatter = container.get("mathematical_formatter")

        # Extract analysis services
        self.layer_analysis_service = container.get("layer_analysis_service")
        self.neuron_selection_service = container.get("neuron_selection_service")
        self.file_service = container.get("file_service")
        self.threshold_service = container.get("threshold_service")
        self.youtube_service = container.get("youtube_service")

        # Extract template environment
        self.env = container.get("template_env")

        # Initialize caches
        self._all_columns_cache = None
        self._column_analysis_cache = {}

        # Extract PageGenerator-dependent services
        self.template_context_service = container.get("template_context_service")
        self.data_processing_service = container.get("data_processing_service")
        self.database_query_service = container.get("database_query_service")
        self.cache_service = container.get("cache_service")
        self.roi_analysis_service = container.get("roi_analysis_service")
        self.column_analysis_service = container.get("column_analysis_service")
        self.url_generation_service = container.get("url_generation_service")
        self.orchestrator = container.get("orchestrator")

        # Copy static files
        self.resource_manager.copy_static_files(self.copy_mode)

    def _init_from_services(self, services):
        """Initialize PageGenerator from pre-configured services."""
        # Extract core services
        self.brain_region_service = services["brain_region_service"]
        self.citation_service = services["citation_service"]
        self.partner_analysis_service = services["partner_analysis_service"]
        self.jinja_template_service = services["jinja_template_service"]
        self.neuron_search_service = services["neuron_search_service"]

        # Extract core data and resources
        self.brain_regions = services["brain_regions"]
        self.citations = services["citations"]
        self.resource_manager = services["resource_manager"]
        self.types_dir = services["types_dir"]
        self.eyemaps_dir = services["eyemaps_dir"]
        self.eyemap_generator = services["hexagon_generator"]

        # Extract utility classes
        self.html_utils = services["html_utils"]
        self.text_utils = services["text_utils"]
        self.number_formatter = services["number_formatter"]
        self.percentage_formatter = services["percentage_formatter"]
        self.synapse_formatter = services["synapse_formatter"]
        self.neurotransmitter_formatter = services["neurotransmitter_formatter"]
        self.mathematical_formatter = services["mathematical_formatter"]

        # Extract analysis services
        self.layer_analysis_service = services["layer_analysis_service"]
        self.neuron_selection_service = services["neuron_selection_service"]
        self.file_service = services["file_service"]
        self.threshold_service = services["threshold_service"]
        self.youtube_service = services["youtube_service"]

        # Extract template environment
        self.env = services["template_env"]

        # Extract caches
        self._all_columns_cache = services["all_columns_cache"]
        self._column_analysis_cache = services["column_analysis_cache"]

        # Services that depend on PageGenerator will be set by factory after initialization
        self.template_context_service = None
        self.data_processing_service = None
        self.database_query_service = services["database_query_service"]
        self.cache_service = None
        self.roi_analysis_service = None
        self.column_analysis_service = None
        self.url_generation_service = None
        self.orchestrator = None

    @classmethod
    def create_with_factory(
        cls,
        config: Config,
        output_dir: str,
        queue_service=None,
        cache_manager=None,
        copy_mode: str = "check_exists",
    ):
        """
        Create PageGenerator using the service factory.

        Args:
            config: Configuration object with template and output settings
            output_dir: Directory path for generated HTML files
            queue_service: Optional QueueService for checking queued neuron types
            cache_manager: Optional cache manager for accessing cached neuron data
            copy_mode: Static file copy mode ("check_exists" for pop, "force_all" for generate)

        Returns:
            Configured PageGenerator instance
        """
        from .services.page_generator_service_factory import PageGeneratorServiceFactory

        return PageGeneratorServiceFactory.create_page_generator(
            config, output_dir, queue_service, cache_manager, copy_mode
        )

    @classmethod
    def create_with_container(
        cls,
        config: Config,
        output_dir: str,
        queue_service=None,
        cache_manager=None,
        copy_mode: str = "check_exists",
    ):
        """
        Create PageGenerator using dependency injection container.

        Args:
            config: Configuration object with template and output settings
            output_dir: Directory path for generated HTML files
            queue_service: Optional QueueService for checking queued neuron types
            cache_manager: Optional cache manager for accessing cached neuron data
            copy_mode: Static file copy mode ("check_exists" for pop, "force_all" for generate)

        Returns:
            Configured PageGenerator instance
        """
        from .services.page_generation_container import PageGenerationContainer

        # Create and configure container
        container = PageGenerationContainer(config)

        # Register optional services
        if queue_service:
            container.register_singleton("queue_service", queue_service)
        if cache_manager:
            container.register_singleton("cache_manager", cache_manager)

        # Create PageGenerator with container
        return cls(
            config=config,
            output_dir=output_dir,
            queue_service=queue_service,
            cache_manager=cache_manager,
            container=container,
            copy_mode=copy_mode,
        )

    def _load_brain_regions(self):
        """Load brain regions data from CSV for the abbr filter."""
        # Delegate to brain region service
        self.brain_regions = self.brain_region_service.load_brain_regions()

    def _load_citations(self):
        """Load citations data from CSV for synonyms links."""
        # Delegate to citation service
        self.citations = self.citation_service.load_citations()

    def _roi_abbr_filter(self, roi_name):
        """
        Convert ROI abbreviation to HTML abbr tag with full name in title.

        Args:
            roi_name: The ROI abbreviation

        Returns:
            HTML abbr tag if full name found, otherwise the original abbreviation
        """
        # Delegate to brain region service
        return self.brain_region_service.roi_abbr_filter(roi_name)

    def _get_partner_body_ids(self, partner_data, direction, connected_bids):
        """
        Return a de-duplicated, order-preserving list of partner bodyIds for a given
        direction, optionally restricted to a soma side.

        Delegates to PartnerAnalysisService for the actual analysis.
        """
        # Delegate to partner analysis service
        return self.partner_analysis_service.get_partner_body_ids(
            partner_data, direction, connected_bids
        )


    def _generate_neuron_search_js(self):
        """Generate neuron-search.js with embedded neuron types data."""
        # Delegate to neuron search service
        self.neuron_search_service.generate_neuron_search_js()

    def _generate_neuroglancer_url(
        self,
        neuron_type: str,
        neuron_data: Dict[str, Any],
        soma_side: Optional[str] = None,
        connector=None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate Neuroglancer URL from template with substituted variables.

        Args:
            neuron_type: The neuron type name
            neuron_data: Data containing neuron information including bodyIDs
            soma_side: Soma side filter ('left', 'right', 'combined', etc.)
            connector: NeuPrint connector instance

        Returns:
            Tuple of (URL-encoded Neuroglancer URL, template variables dict)
        """
        # Delegate to the URL generation service
        return self.url_generation_service.generate_neuroglancer_url(
            neuron_type, neuron_data, soma_side, connector
        )




    def _generate_neuprint_url(
        self, neuron_type: str, neuron_data: Dict[str, Any]
    ) -> str:
        """
        Generate NeuPrint URL from template with substituted variables.

        Args:
            neuron_type: The neuron type name
            neuron_data: Data containing neuron information

        Returns:
            NeuPrint URL for searching this neuron type
        """
        # Delegate to the URL generation service
        return self.url_generation_service.generate_neuprint_url(
            neuron_type, neuron_data
        )


    def generate_page_unified(self, request: PageGenerationRequest):
        """
        Generate an HTML page using the unified orchestrator workflow.

        This is the modern unified method that replaces the legacy generate_page
        method. It provides a single interface for all page generation needs with
        full analysis capabilities, error handling, and consistent response format.

        Features:
        - Unified interface for raw neuron data workflows
        - Comprehensive analysis (ROI, layer, column) for all generation modes
        - Robust error handling with detailed response metadata
        - Support for all visualization options (SVG/PNG, embedding, compression)
        - Performance optimization through modern service architecture

        Args:
            request: PageGenerationRequest containing all generation parameters

        Returns:
            PageGenerationResponse with the result including output path and metadata

        Example:
            from .models.page_generation import PageGenerationRequest

            request = PageGenerationRequest(
                neuron_type="LPLC2",
                soma_side="left",
                neuron_data=connector.get_neuron_data("LPLC2", "left"),
                connector=connector,
                image_format="svg",
                embed_images=False,
                minify=True,
                run_roi_analysis=True,
                run_layer_analysis=True,
                run_column_analysis=True
            )

            response = generator.generate_page_unified(request)
            if response.success:
                print(f"Generated: {response.output_path}")
            else:
                print(f"Error: {response.error_message}")
        """
        return self.orchestrator.generate_page(request)

    def _aggregate_roi_data(self, roi_counts_df, neurons_df, soma_side, connector=None):
        """Aggregate ROI data across neurons matching the specific soma side to get total pre/post synapses per ROI (primary ROIs only)."""
        return self.data_processing_service.aggregate_roi_data(
            roi_counts_df, neurons_df, soma_side, connector
        )

    def _analyze_layer_roi_data(
        self, roi_counts_df, neurons_df, soma_side, neuron_type, connector
    ):
        """
        Analyze ROI data for layer-based regions matching pattern (ME|LO|LOP)_[LR]_layer_<number>.
        When layer innervation is detected, also include AME, LA, and centralBrain regions.
        Returns additional table with layer-specific synapse counts.

        Args:
            roi_counts_df: DataFrame with ROI count data
            neurons_df: DataFrame with neuron data
            soma_side: Side of soma (left/right)
            neuron_type: Name of the neuron type
            connector: Database connector for additional queries
        """
        # Delegate to the layer analysis service
        return self.layer_analysis_service.analyze_layer_roi_data(
            roi_counts_df, neurons_df, soma_side, neuron_type, connector
        )

    def _get_all_dataset_layers(self, layer_pattern, connector):
        """
        Query the entire dataset for all available layer patterns.

        Args:
            layer_pattern: Regex pattern to match layer ROIs
            connector: NeuPrint connector to query the database

        Returns:
            List of tuples: (region, side, layer_num) for all layers in dataset
        """
        return self.roi_analysis_service.get_all_dataset_layers(
            layer_pattern, connector
        )

    def _get_columns_for_neuron_type(self, connector, neuron_type: str):
        """
        Query the dataset to get column coordinates that exist for a specific neuron type.
        This optimized version only processes the requested neuron type instead of all neurons.

        Args:
            connector: NeuPrint connector instance for database queries
            neuron_type: Specific neuron type to analyze

        Returns:
            Tuple of (type_columns, region_columns_map) where:
            - type_columns: List of dicts with hex1, hex2 (integers) for this type
            - region_columns_map: Dict mapping region_side names to sets of (hex1, hex2) tuples
        """
        return self.roi_analysis_service.get_columns_for_neuron_type(
            connector, neuron_type
        )

    def _get_columns_from_neuron_cache(self, neuron_type: str):
        """
        Extract column data from neuron type cache if available.

        Args:
            neuron_type: The neuron type to get cached column data for

        Returns:
            Tuple of (columns_data, region_columns_map) or (None, None) if not cached
        """
        return self.cache_service.get_columns_from_neuron_cache(neuron_type)


    def _load_persistent_columns_cache(self, cache_key):
        """Load persistent cache for all columns dataset query."""
        return self.cache_service.load_persistent_columns_cache(cache_key)

    # def _save_persistent_columns_cache(self, cache_key, result):
    #     """Save persistent cache for all columns dataset query."""
    #     # DISABLED: No longer saving standalone columns cache - using neuron cache instead
    #     pass

    def _analyze_column_roi_data(
        self,
        roi_counts_df,
        neurons_df,
        soma_side,
        neuron_type,
        connector,
        file_type: str = "svg",
        save_to_files: bool = True,
        hex_size: int = 6,
        spacing_factor: float = 1.1,
    ):
        """
        Analyze ROI data for column-based regions matching pattern (ME|LO|LOP)_[RL]_col_hex1_hex2.
        Returns additional table with mean synapses per column per neuron type.
        Now includes comprehensive hexagonal grids showing all possible columns.

        This method uses caching to avoid expensive repeated column analysis.

        Args:
            roi_counts_df: DataFrame with ROI count data
            neurons_df: DataFrame with neuron data
            soma_side: Side of soma (left/right)
            neuron_type: Type of neuron being analyzed
            connector: NeuPrint connector instance for database queries
            file_type: Output format for hexagonal grids ('svg' or 'png')
            save_to_files: If True, save files to disk; if False, embed content
            hex_size: Size of hexagons in visualization
            spacing_factor: Spacing factor between hexagons
        """
        # Delegate to the column analysis service
        return self.column_analysis_service.analyze_column_roi_data(
            roi_counts_df,
            neurons_df,
            soma_side,
            neuron_type,
            connector,
            file_type,
            save_to_files,
            hex_size,
            spacing_factor,
        )


    def _compute_thresholds(self, df: pd.DataFrame, n_bins: int = 5):
        """
        Compute threshold lists for synapse and neuron counts at different aggregation levels.

        Delegates to ThresholdService for the actual computation.
        """
        return self.threshold_service.compute_thresholds(df, n_bins)

    def _layer_thresholds(self, values, n_bins=5):
        """
        Return n_bins+1 thresholds from min..max for a 1D list of numbers.

        Delegates to ThresholdService for the actual computation.
        """
        return self.threshold_service.layer_thresholds(values, n_bins)

    def _generate_region_hexagonal_grids(
        self,
        column_summary: List[Dict],
        neuron_type: str,
        soma_side,
        file_type: str = "svg",
        save_to_files: bool = True,
        connector=None,
        min_max_data: Optional[Dict] = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate separate hexagonal grid visualizations for each region (ME, LO, LOP).

        Args:
            column_summary: List of column data dictionaries
            neuron_type: Name of the neuron type
            soma_side: Soma side being analyzed
            file_type: Output format ('svg' or 'png')
            save_to_files: If True, save files to output/static/images and return file paths.
                          If False, return content directly for embedding in HTML.
            connector: NeuPrint connector for getting dataset information

        Returns:
            Dictionary mapping region names to visualization data (either file paths or content)
        """
        if file_type not in ["svg", "png"]:
            raise ValueError("file_type must be either 'svg' or 'png'")

        # Compute thresholds from column_summary
        df = pd.DataFrame(column_summary)
        thresholds_all = self._compute_thresholds(df, n_bins=5) if not df.empty else {}

        # Get all possible columns from the dataset if connector is available
        all_possible_columns = []
        region_columns_map = {}
        if connector:
            all_possible_columns, region_columns_map = (
                self.database_query_service.get_all_possible_columns_from_dataset(
                    connector
                )
            )

        # Convert dictionary input to structured ColumnData objects
        column_data = DataAdapter.normalize_input(column_summary)

        # Convert string soma_side to SomaSide enum
        soma_side_enum = (
            SomaSide(soma_side) if isinstance(soma_side, str) else soma_side
        )

        # Create request object for new API
        request = create_grid_generation_request(
            column_data=column_data,
            thresholds_all=thresholds_all,
            all_possible_columns=all_possible_columns,
            region_columns_map=region_columns_map,
            neuron_type=neuron_type,
            soma_side=soma_side_enum,
            output_format=file_type,
            save_to_files=save_to_files,
            min_max_data=min_max_data or {},
        )

        # Call with new API
        result = self.eyemap_generator.generate_comprehensive_region_hexagonal_grids(
            request
        )

        return result.region_grids


    def clean_dynamic_files_for_neuron(
        self, neuron_type: str, soma_side: str = None
    ) -> bool:
        """
        Clean dynamic files (HTML pages and eyemaps) for a specific neuron type.

        This is useful when regenerating pages to ensure fresh content.

        Args:
            neuron_type: Name of the neuron type
            soma_side: Optional soma side filter. If None, cleans all soma sides for the neuron type

        Returns:
            True if successful, False otherwise
        """
        return self.resource_manager.clean_dynamic_files(neuron_type, soma_side)

    @staticmethod
    def generate_filename(neuron_type: str, soma_side: str) -> str:
        """
        Generate HTML filename for a neuron type and soma side.

        This is a static utility method that doesn't require PageGenerator instantiation.
        Delegates to FileService for the actual generation.

        Args:
            neuron_type: The neuron type name
            soma_side: The soma side ('left', 'right', 'middle', 'all', 'combined')

        Returns:
            HTML filename string
        """
        return FileService.generate_filename(neuron_type, soma_side)


    def _find_youtube_video(self, neuron_type: str) -> Optional[str]:
        """
        Find YouTube video ID for a neuron type by matching against descriptions.

        Args:
            neuron_type: Name of the neuron type (without soma side)

        Returns:
            YouTube video ID if found, None otherwise
        """
        return self.youtube_service.find_youtube_video(neuron_type)

    def _get_primary_rois(self, connector):
        """Get primary ROIs based on dataset type and available data."""
        return self.roi_analysis_service.get_primary_rois(connector)


    def _get_region_for_type(self, neuron_type: str, connector) -> str:
        """Find the type's assigned "region" - used for setting the NG view."""
        return self.roi_analysis_service.get_region_for_type(neuron_type, connector)
