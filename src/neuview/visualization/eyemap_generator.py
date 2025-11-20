"""
Hexagon grid generator for visualizing column data.

This module provides hexagon grid generation functionality supporting SVG
and PNG output formats using Cairo for enhanced visualization capabilities.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union

from .color import ColorMapper, ColorPalette
from .config_manager import EyemapConfiguration
from .constants import (
    METRIC_CELL_COUNT,
    METRIC_SYNAPSE_DENSITY,
    TOOLTIP_CELL_LABEL,
    TOOLTIP_SYNAPSE_LABEL,
)
from .coordinate_system import EyemapCoordinateSystem
from .data_processing import DataProcessor
from .data_processing.data_structures import (
    ColumnStatus,
    MetricType,
    ProcessingConfig,
    SomaSide,
)
from .data_transfer_objects import (
    GridGenerationRequest,
    GridGenerationResult,
    SingleRegionGridRequest,
    create_rendering_request,
)
from .dependency_injection import EyemapServiceContainer, get_default_container
from .exceptions import (
    DataProcessingError,
    ErrorContext,
    EyemapError,
    RenderingError,
    ValidationError,
    safe_operation,
)
from .file_output_manager import FileOutputManagerFactory
from .performance import (
    MemoryOptimizer,
    PerformanceOptimizerFactory,
    get_performance_monitor,
    performance_timer,
)
from .region_grid_processor import RegionGridProcessorFactory
from .rendering import RenderingManager
from .validation import EyemapRequestValidator, EyemapRuntimeValidator

logger = logging.getLogger(__name__)


class EyemapGenerator:
    """
    Generate hexagonal grid visualizations for column data.

    Supports SVG and PNG output formats with consistent styling and
    color mapping across different metrics and regions.
    """

    def __init__(
        self,
        config: EyemapConfiguration,
        enable_performance_optimization: bool = True,
        service_container: Optional[EyemapServiceContainer] = None,
    ):
        """
        Initialize the eyemap generator with dependency injection support.

        Args:
            config: Unified configuration object (required)
            enable_performance_optimization: Whether to enable performance optimizations
            service_container: Optional service container for dependency injection

        Raises:
            ValidationError: If configuration parameters are invalid
            DependencyError: If service container setup fails
        """
        with ErrorContext("eyemap_generator_initialization"):
            # Validate required configuration
            if not isinstance(config, EyemapConfiguration):
                raise ValidationError(
                    "config parameter must be an EyemapConfiguration instance",
                    field="config",
                    value=type(config).__name__,
                    expected_type=EyemapConfiguration,
                )

            # Initialize or validate service container
            if service_container is not None:
                self.container = service_container
            else:
                # Create service container with configuration
                self.container = EyemapServiceContainer(config)

            # Store configuration
            self.config = config

            # Convenience properties for direct access
            self.hex_size = self.config.hex_size
            self.spacing_factor = self.config.spacing_factor
            self.output_dir = self.config.output_dir
            self.eyemaps_dir = self.config.eyemaps_dir
            self.embed_mode = self.config.embed_mode

            # Initialize core services
            try:
                # Core visualization services
                self.color_palette = self.container.resolve(ColorPalette)
                self.color_mapper = self.container.resolve(ColorMapper)
                self.coordinate_system = self.container.resolve(EyemapCoordinateSystem)
                self.data_processor = self.container.resolve(DataProcessor)
                self.rendering_manager = self.container.resolve(RenderingManager)

                # Resolve factory services
                region_factory = self.container.resolve(RegionGridProcessorFactory)
                self.region_processor = region_factory.create_processor(
                    self.data_processor
                )

                file_factory = self.container.resolve(FileOutputManagerFactory)
                self.file_manager = file_factory.create_from_config(self.config)

                # Initialize performance optimization components
                if enable_performance_optimization:
                    self.memory_optimizer = self.container.try_resolve(MemoryOptimizer)
                    self.performance_monitor = self.container.try_resolve(
                        type(get_performance_monitor())
                    )
                    optimizer_factory = self.container.try_resolve(
                        PerformanceOptimizerFactory
                    )
                    self.optimizers = (
                        optimizer_factory.create_full_optimizer_suite()
                        if optimizer_factory
                        else None
                    )
                else:
                    self.memory_optimizer = None
                    self.performance_monitor = None
                    self.optimizers = None

                # Initialize validators
                self.request_validator = EyemapRequestValidator()
                self.runtime_validator = EyemapRuntimeValidator()

                logger.debug("EyemapGenerator initialized successfully")

            except Exception as e:
                logger.error(f"Failed to resolve services from container: {e}")
                raise

    @classmethod
    def create_with_defaults(cls, **config_overrides) -> "EyemapGenerator":
        """
        Create an EyemapGenerator with default configuration and dependency injection.

        Args:
            **config_overrides: Configuration parameters to override

        Returns:
            Configured EyemapGenerator instance

        Raises:
            ValidationError: If configuration is invalid
        """
        container = get_default_container()
        if config_overrides:
            # Create updated configuration
            base_config = container.resolve(EyemapConfiguration)
            updated_config = base_config.update(**config_overrides)
            # Create new container with updated config
            container = EyemapServiceContainer(updated_config)

        return cls(service_container=container)

    @classmethod
    def create_from_container(
        cls, container: EyemapServiceContainer
    ) -> "EyemapGenerator":
        """
        Create an EyemapGenerator from an existing service container.

        Args:
            container: Configured service container

        Returns:
            EyemapGenerator instance using the provided container
        """
        return cls(service_container=container)

    @performance_timer("generate_comprehensive_region_hexagonal_grids")
    @performance_timer("comprehensive_grid_generation")
    def generate_comprehensive_region_hexagonal_grids(
        self, request: GridGenerationRequest
    ) -> GridGenerationResult:
        """
        Generate comprehensive hexagonal grid visualizations showing all possible columns.

        This method handles comprehensive grid generation with proper validation
        and error handling for complex multi-region workflows.

        Args:
            request: GridGenerationRequest containing all generation parameters

        Returns:
            GridGenerationResult with generation results and metadata

        Raises:
            ValidationError: If request validation fails
            DataProcessingError: If data processing fails
        """
        with ErrorContext(
            "comprehensive_grid_generation",
            regions=len(request.regions) if request.regions else 0,
        ):
            start_time = time.time()

            # Process comprehensive grid generation request
            try:
                # Validate request thoroughly
                self.request_validator.validate_grid_generation_request(request)
            except ValidationError as e:
                logger.error(f"Request validation failed: {e}")
                return GridGenerationResult(
                    region_grids={},
                    processing_time=time.time() - start_time,
                    success=False,
                    error_message=f"Request validation failed: {e.message}",
                )

            # Set embed mode based on save_to_files parameter
            self.embed_mode = not request.save_to_files
            self.config.update(
                embed_mode=self.embed_mode, save_to_files=request.save_to_files
            )

            warnings = []

            try:
                # Organize data by side with error handling
                data_maps = safe_operation(
                    "organize_data_by_side", self._organize_data_by_side, request
                )

                # Process all regions and sides to generate grids using the processor
                processed_grids = safe_operation(
                    "process_all_regions_and_sides",
                    self.region_processor.process_all_regions_and_sides,
                    request,
                    data_maps,
                    self.generate_comprehensive_single_region_grid,
                )

                # Handle output for all processed grids
                region_grids = safe_operation(
                    "handle_all_grid_outputs",
                    self._handle_all_grid_outputs,
                    request,
                    processed_grids,
                )

                processing_time = time.time() - start_time
                logger.debug(
                    f"Successfully generated grids for {len(region_grids)} region combinations in {processing_time:.2f}s"
                )

                return GridGenerationResult(
                    region_grids=region_grids,
                    processing_time=processing_time,
                    success=True,
                    warnings=warnings,
                )

            except EyemapError as e:
                processing_time = time.time() - start_time
                logger.error(f"Grid generation failed: {e}")
                return GridGenerationResult(
                    region_grids={},
                    processing_time=processing_time,
                    success=False,
                    error_message=str(e),
                )
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Unexpected error during grid generation: {e}")
                return GridGenerationResult(
                    region_grids={},
                    processing_time=processing_time,
                    success=False,
                    error_message=f"Unexpected error: {str(e)}",
                )

    def _organize_data_by_side(self, request: GridGenerationRequest) -> Dict:
        """
        Organize column data by soma side using the data processor.

        Args:
            request: GridGenerationRequest containing column data and soma side info

        Returns:
            Dictionary mapping sides to their organized data maps
        """
        # Convert soma_side string to SomaSide enum
        from .data_processing.data_structures import SomaSide

        if isinstance(request.soma_side, str):
            if request.soma_side.lower() in ["combined"]:
                soma_side_enum = SomaSide.COMBINED
            elif request.soma_side.lower() in ["left", "l"]:
                soma_side_enum = SomaSide.LEFT
            elif request.soma_side.lower() in ["right", "r"]:
                soma_side_enum = SomaSide.RIGHT
            else:
                # Default to combined
                soma_side_enum = SomaSide.COMBINED
        elif hasattr(request.soma_side, "value"):
            # It's already a SomaSide enum
            soma_side_enum = request.soma_side
        else:
            # Handle other cases - convert to string first
            soma_side_str = str(request.soma_side)
            if soma_side_str.lower() in ["combined"]:
                soma_side_enum = SomaSide.COMBINED
            elif soma_side_str.lower() in ["left", "l"]:
                soma_side_enum = SomaSide.LEFT
            elif soma_side_str.lower() in ["right", "r"]:
                soma_side_enum = SomaSide.RIGHT
            else:
                soma_side_enum = SomaSide.COMBINED

        # Use the modernized structured data organization
        return self.data_processor.column_data_manager.organize_structured_data_by_side(
            request.column_data, soma_side_enum
        )

    def _handle_all_grid_outputs(
        self, request: GridGenerationRequest, processed_grids: Dict
    ) -> Dict:
        """
        Handle output for all processed grids using the file output manager.

        Args:
            request: GridGenerationRequest containing output configuration
            processed_grids: Dictionary of processed grids from region processor

        Returns:
            Dictionary mapping region_side keys to their final output
        """
        region_grids = {}

        for region_side_key, grid_data in processed_grids.items():
            region = grid_data["region"]
            side = grid_data["side"]
            synapse_content = grid_data["synapse_content"]
            cell_content = grid_data["cell_content"]

            # Use file manager to handle output
            region_grids[region_side_key] = self.file_manager.handle_grid_output(
                request,
                region,
                side,
                synapse_content,
                cell_content,
                self.rendering_manager,
            )

        return region_grids

    @performance_timer("generate_comprehensive_single_region_grid")
    @performance_timer("single_region_grid_generation")
    def generate_comprehensive_single_region_grid(
        self, request: SingleRegionGridRequest
    ) -> str:
        """
        Generate comprehensive hexagonal grid showing all possible columns for a single region.

        This method handles single region grid generation with proper validation
        and error handling for individual region workflows.

        Args:
            request: SingleRegionGridRequest containing all generation parameters

        Returns:
            Generated visualization content as string

        Raises:
            ValidationError: If request validation fails
            DataProcessingError: If data processing fails
            RenderingError: If visualization rendering fails
        """
        with ErrorContext(
            "single_region_grid_generation",
            region=request.region_name,
            side=request.soma_side,
            metric=request.metric_type,
        ):
            try:
                # Process single region grid generation request
                # Validate request thoroughly
                self.request_validator.validate_single_region_request(request)

                # Validate runtime preconditions
                self.runtime_validator.validate_operation_preconditions(
                    "single_region_grid_generation",
                    has_columns=bool(request.all_possible_columns),
                    has_region=bool(request.region_name),
                    has_side=bool(request.soma_side),
                    has_metric=bool(request.metric_type),
                )

                value_range = safe_operation(
                    "determine_value_range",
                    self._determine_value_range,
                    request.thresholds,
                )

                # Set up visualization metadata
                if request.metric_type == METRIC_SYNAPSE_DENSITY:
                    plot_desc = "Synapses (All Columns)"
                    # Handle both string and SomaSide enum inputs
                    if hasattr(request.soma_side, "value"):
                        soma_display = (
                            request.soma_side.value.upper()[:1]
                            if request.soma_side
                            else ""
                        )
                    else:
                        soma_display = (
                            str(request.soma_side).upper()[:1]
                            if request.soma_side
                            else ""
                        )
                    neuron_desc = f"{request.region_name} ({soma_display})"
                    region_desc = f"{request.neuron_type} ({soma_display})"
                else:  # cell_count
                    plot_desc = "Cell Count (All Columns)"
                    # Handle both string and SomaSide enum inputs
                    if hasattr(request.soma_side, "value"):
                        soma_display = (
                            request.soma_side.value.upper()[:1]
                            if request.soma_side
                            else ""
                        )
                    else:
                        soma_display = (
                            str(request.soma_side).upper()[:1]
                            if request.soma_side
                            else ""
                        )
                    neuron_desc = f"{request.region_name} ({soma_display})"
                    region_desc = f"{request.neuron_type} ({soma_display})"

                grid_metadata = {
                    "plot_desc": plot_desc,
                    "neuron_desc": neuron_desc,
                    "region_desc": region_desc,
                }

                # Create processing configuration
                processing_config = safe_operation(
                    "create_processing_configuration",
                    self._create_processing_configuration,
                    request,
                )

                # Process the data
                with ErrorContext("single_region_data_processing"):
                    # Validate required data exists
                    self.runtime_validator.validate_data_consistency(
                        {
                            "all_possible_columns": request.all_possible_columns,
                            "region_column_coords": getattr(
                                request, "region_column_coords", None
                            ),
                            "data_map": getattr(request, "data_map", None),
                        },
                        {"all_possible_columns"},
                        "single_region_data_processing",
                    )

                    processing_result = self.data_processor._process_side_data(
                        request.all_possible_columns,
                        getattr(request, "region_column_coords", None),
                        getattr(request, "data_map", None),
                        processing_config,
                        getattr(request, "other_regions_coords", set()) or set(),
                        getattr(request, "thresholds", None),
                        getattr(request, "min_max_data", None),
                        getattr(request, "soma_side", "right") or "right",
                    )

                    # Validate result
                    if not hasattr(processing_result, "is_successful"):
                        raise DataProcessingError(
                            "Data processor returned invalid result format",
                            operation="single_region_data_processing",
                        )

                if not processing_result.is_successful:
                    error_details = (
                        processing_result.validation_result.errors
                        if hasattr(processing_result, "validation_result")
                        else "Unknown processing error"
                    )
                    raise DataProcessingError(
                        f"Data processing failed: {error_details}",
                        operation="process_single_region_data",
                    )

                # Convert coordinates
                with ErrorContext("coordinate_to_pixel_conversion"):
                    # Validate input
                    if not request.all_possible_columns:
                        raise DataProcessingError(
                            "Cannot convert coordinates from empty column list",
                            operation="coordinate_to_pixel_conversion",
                        )

                    # Convert coordinates to pixels
                    # Use same mirror_side determination logic as data processor
                    mirror_side = self._determine_mirror_side_with_context(
                        request.soma_side, None
                    )
                    columns_with_coords = (
                        self.coordinate_system.convert_column_coordinates(
                            request.all_possible_columns, mirror_side=mirror_side
                        )
                    )

                    # Validate conversion result
                    if not columns_with_coords:
                        raise DataProcessingError(
                            "Coordinate conversion returned empty result",
                            operation="coordinate_to_pixel_conversion",
                        )

                    coord_to_pixel = {
                        (col["hex1"], col["hex2"]): {"x": col["x"], "y": col["y"]}
                        for col in columns_with_coords
                    }

                    logger.debug(
                        f"Converted {len(coord_to_pixel)} coordinate pairs to pixels"
                    )

                # Create hexagon data collection
                with ErrorContext("hexagon_data_collection_creation"):
                    # Validate inputs
                    if not hasattr(processing_result, "processed_columns"):
                        raise DataProcessingError(
                            "Processing result missing processed_columns attribute",
                            operation="hexagon_data_collection_creation",
                        )

                    if not coord_to_pixel:
                        raise DataProcessingError(
                            "Coordinate to pixel mapping is empty",
                            operation="hexagon_data_collection_creation",
                        )

                    # Process hexagon columns
                    hexagons = []
                    min_value = value_range["min_value"]
                    max_value = value_range["max_value"]
                    skipped_count = 0

                    if (
                        not hasattr(processing_result, "processed_columns")
                        or not processing_result.processed_columns
                    ):
                        logger.warning(
                            "No processed columns available for hexagon creation"
                        )
                        hexagons = []
                    else:
                        for i, processed_col in enumerate(
                            processing_result.processed_columns
                        ):
                            try:
                                # Validate processed column structure
                                if not hasattr(processed_col, "hex1") or not hasattr(
                                    processed_col, "hex2"
                                ):
                                    logger.warning(
                                        f"Processed column at index {i} missing hex coordinates, skipping"
                                    )
                                    skipped_count += 1
                                    continue

                                coord_tuple = (processed_col.hex1, processed_col.hex2)

                                if coord_tuple not in coord_to_pixel:
                                    skipped_count += 1
                                    continue

                                pixel_coords = coord_to_pixel[coord_tuple]

                                # Get raw data for layer colors
                                layer_colors = safe_operation(
                                    "extract_layer_colors",
                                    self._extract_layer_colors,
                                    processed_col,
                                    request,
                                )

                                # Determine hexagon color
                                if processed_col.status == ColumnStatus.HAS_DATA:
                                    color = self.color_mapper.map_value_to_color(
                                        processed_col.value, min_value, max_value
                                    )
                                elif processed_col.status == ColumnStatus.NO_DATA:
                                    color = self.color_palette.white
                                elif processed_col.status == ColumnStatus.NOT_IN_REGION:
                                    color = self.color_palette.dark_gray
                                else:
                                    color = None

                                if color is None:
                                    skipped_count += 1
                                    continue

                                layer_values = getattr(
                                    processed_col, "layer_values", []
                                )
                                hexagon_data = {
                                    "x": pixel_coords["x"],
                                    "y": pixel_coords["y"],
                                    "value": getattr(processed_col, "value", None),
                                    "layer_values": layer_values,
                                    "layer_colors": layer_colors,
                                    "color": color,
                                    "region": getattr(request, "region_name", ""),
                                    "side": "combined",  # Since we're showing all possible columns
                                    "hex1": processed_col.hex1,
                                    "hex2": processed_col.hex2,
                                    "neuron_count": getattr(processed_col, "value", 0)
                                    if getattr(request, "metric_type", "")
                                    == METRIC_CELL_COUNT
                                    else 0,
                                    "column_name": f"{getattr(request, 'region_name', 'unknown')}_col_{processed_col.hex1}_{processed_col.hex2}",
                                    "synapse_value": getattr(processed_col, "value", 0)
                                    if getattr(request, "metric_type", "")
                                    == METRIC_SYNAPSE_DENSITY
                                    else 0,
                                    "status": getattr(
                                        processed_col, "status", "unknown"
                                    ).value
                                    if hasattr(
                                        getattr(processed_col, "status", None), "value"
                                    )
                                    else "unknown",
                                    "metric_type": getattr(request, "metric_type", ""),
                                }

                                hexagons.append(hexagon_data)

                            except Exception as e:
                                logger.warning(
                                    f"Failed to process hexagon at index {i}: {e}"
                                )
                                skipped_count += 1
                                continue

                        if skipped_count > 0:
                            logger.info(
                                f"Skipped {skipped_count} hexagons during processing"
                            )

                    logger.debug(f"Created {len(hexagons)} hexagon data objects")

                # Finalize visualization
                # Add tooltips to hexagons before rendering
                hexagons_with_tooltips = self._generate_tooltips_for_hexagons(
                    hexagons=hexagons,
                    soma_side=request.soma_side or "right",
                    metric_type=request.metric_type,
                    region=request.region_name,
                )

                from .data_processing.data_structures import SomaSide

                # Create rendering request
                rendering_request = create_rendering_request(
                    hexagons=hexagons_with_tooltips,
                    min_val=value_range["min_value"],
                    max_val=value_range["max_value"],
                    thresholds=request.thresholds or {},
                    plot_desc=grid_metadata["plot_desc"],
                    neuron_desc=grid_metadata["neuron_desc"],
                    region_desc=grid_metadata["region_desc"],
                    metric_type=request.metric_type,
                    soma_side=request.soma_side or SomaSide.RIGHT,
                    min_max_data=request.min_max_data,
                )

                # Use rendering manager to generate visualization
                soma_side_str = rendering_request.soma_side.value

                # Convert output format string to OutputFormat enum
                from .rendering.rendering_config import OutputFormat

                if isinstance(rendering_request.output_format, str):
                    if rendering_request.output_format.lower() == "svg":
                        output_format_enum = OutputFormat.SVG
                    elif rendering_request.output_format.lower() == "png":
                        output_format_enum = OutputFormat.PNG
                    else:
                        output_format_enum = OutputFormat.SVG  # Default fallback
                else:
                    output_format_enum = rendering_request.output_format

                # Convert soma_side string to SomaSide enum for modern API
                try:
                    if soma_side_str:
                        # Handle different string formats
                        if soma_side_str.lower() in ["left", "l"]:
                            soma_side_enum = SomaSide.LEFT
                        elif soma_side_str.lower() in ["right", "r"]:
                            soma_side_enum = SomaSide.RIGHT
                        elif soma_side_str.lower() in ["combined"]:
                            soma_side_enum = SomaSide.COMBINED
                        else:
                            soma_side_enum = SomaSide.RIGHT  # Default fallback
                    else:
                        soma_side_enum = SomaSide.RIGHT  # Default fallback
                except (ValueError, AttributeError):
                    soma_side_enum = SomaSide.RIGHT  # Default fallback

                # Update rendering manager configuration with rendering parameters
                updated_config = self.rendering_manager.config.copy(
                    plot_desc=rendering_request.plot_desc,
                    neuron_desc=rendering_request.neuron_desc,
                    region_desc=rendering_request.region_desc,
                    metric_type=rendering_request.metric_type,
                    soma_side=soma_side_enum,
                    thresholds=rendering_request.thresholds,
                    save_to_files=rendering_request.save_to_file,
                    min_max_data=rendering_request.min_max_data,
                )

                # Create temporary manager with updated config
                from .rendering.rendering_manager import RenderingManager

                temp_manager = RenderingManager(
                    updated_config, self.rendering_manager.color_mapper
                )

                # Calculate layout and legend
                region = (
                    rendering_request.hexagons[0].get("region")
                    if rendering_request.hexagons
                    else None
                )
                layout_config = temp_manager.layout_calculator.calculate_layout(
                    rendering_request.hexagons, soma_side_enum, region
                )
                legend_config = temp_manager.layout_calculator.calculate_legend_config(
                    rendering_request.hexagons,
                    rendering_request.thresholds,
                    rendering_request.metric_type,
                )

                # Use modern render method
                result = temp_manager.render(
                    hexagons=rendering_request.hexagons,
                    output_format=output_format_enum,
                    layout_config=layout_config,
                    legend_config=legend_config,
                    save_to_file=rendering_request.save_to_file,
                    filename=f"{rendering_request.plot_desc}_{rendering_request.neuron_desc}_{rendering_request.region_desc}"
                    if rendering_request.save_to_file
                    else None,
                )

                # Validate result integrity
                self.runtime_validator.validate_result_integrity(
                    result,
                    str,
                    "single_region_grid_generation",
                    additional_checks={
                        "non_empty": lambda r: bool(r.strip()),
                        "valid_svg": lambda r: "<svg" in r
                        if request.output_format != "png"
                        else True,
                    },
                )

                logger.debug(
                    f"Successfully generated single region grid for {request.region_name}/{request.soma_side}/{request.metric_type}"
                )
                return result

            except (ValidationError, DataProcessingError, RenderingError) as e:
                logger.error(f"Single region grid generation failed: {e}")
                return ""
            except Exception as e:
                logger.error(f"Unexpected error in single region grid generation: {e}")
                raise DataProcessingError(
                    f"Single region grid generation failed: {str(e)}",
                    operation="single_region_grid_generation",
                ) from e

    def _calculate_coordinate_ranges(
        self, all_possible_columns: List[Dict]
    ) -> Dict[str, int]:
        """
        Calculate coordinate ranges from all possible columns.

        Analyzes the hex1 and hex2 coordinates across all columns to determine
        the minimum values. This is used for coordinate system calculations
        and grid positioning.

        Args:
            all_possible_columns: List of column dictionaries with hex1, hex2 coordinates

        Returns:
            Dictionary containing min_hex1 and min_hex2 values

        Raises:
            DataProcessingError: If coordinate calculation fails
        """
        with ErrorContext("coordinate_range_calculation"):
            try:
                # Validate input
                if not all_possible_columns:
                    raise DataProcessingError(
                        "Cannot calculate coordinate ranges from empty column list",
                        operation="coordinate_range_calculation",
                    )

                # Validate required fields exist
                for i, col in enumerate(all_possible_columns):
                    if "hex1" not in col or "hex2" not in col:
                        raise DataProcessingError(
                            f"Column at index {i} missing required coordinates (hex1/hex2)",
                            operation="coordinate_range_calculation",
                            data_context={
                                "column_index": i,
                                "available_keys": list(col.keys()),
                            },
                        )

                # Calculate ranges with validation
                hex1_values = [col["hex1"] for col in all_possible_columns]
                hex2_values = [col["hex2"] for col in all_possible_columns]

                if not all(
                    isinstance(v, (int, float)) for v in hex1_values + hex2_values
                ):
                    raise DataProcessingError(
                        "All coordinate values must be numeric",
                        operation="coordinate_range_calculation",
                    )

                result = {"min_hex1": min(hex1_values), "min_hex2": min(hex2_values)}

                logger.debug(f"Calculated coordinate ranges: {result}")
                return result

            except Exception as e:
                if isinstance(e, DataProcessingError):
                    raise
                raise DataProcessingError(
                    f"Failed to calculate coordinate ranges: {str(e)}",
                    operation="coordinate_range_calculation",
                ) from e

    def _determine_value_range(self, thresholds: Optional[Dict]) -> Dict[str, float]:
        """
        Determine the value range from thresholds.

        Extracts the minimum and maximum values from the threshold configuration
        to establish the color mapping range. Falls back to default range of 0-1
        if no thresholds are provided.

        Args:
            thresholds: Optional threshold dictionary containing 'all' key with min/max values

        Returns:
            Dictionary containing global_min, global_max, min_value, max_value, and value_range

        Raises:
            DataProcessingError: If threshold values are invalid
        """
        with ErrorContext("value_range_determination"):
            try:
                # Extract thresholds with validation
                if thresholds and "all" in thresholds and thresholds["all"]:
                    threshold_values = thresholds["all"]

                    # Validate threshold structure
                    if (
                        not isinstance(threshold_values, (list, tuple))
                        or len(threshold_values) < 2
                    ):
                        raise DataProcessingError(
                            "Threshold 'all' values must be a list/tuple with at least 2 elements",
                            operation="value_range_determination",
                            data_context={"threshold_values": str(threshold_values)},
                        )

                    # Validate threshold values are numeric
                    if not all(
                        isinstance(v, (int, float)) and not (v != v)
                        for v in threshold_values
                    ):  # NaN check
                        raise DataProcessingError(
                            "All threshold values must be finite numbers",
                            operation="value_range_determination",
                            data_context={"threshold_values": str(threshold_values)},
                        )

                    global_min = threshold_values[0]
                    global_max = threshold_values[-1]

                    # Handle degenerate case where all values are equal
                    if global_min == global_max:
                        # Create a small artificial range for visualization
                        epsilon = 0.1 if global_min != 0 else 0.1
                        global_min = global_min - epsilon
                        global_max = global_max + epsilon
                        logger.debug(
                            f"Adjusted degenerate range: {global_min} to {global_max}"
                        )
                    elif global_min > global_max:
                        raise DataProcessingError(
                            f"Threshold minimum ({global_min}) must be less than maximum ({global_max})",
                            operation="value_range_determination",
                            data_context={"min": global_min, "max": global_max},
                        )
                else:
                    # Default range
                    global_min = 0
                    global_max = 1

                min_value = global_min if global_min is not None else 0
                max_value = global_max if global_max is not None else 1
                value_range = max_value - min_value if max_value > min_value else 1

                result = {
                    "global_min": global_min,
                    "global_max": global_max,
                    "min_value": min_value,
                    "max_value": max_value,
                    "value_range": value_range,
                }

                logger.debug(f"Determined value range: {result}")
                return result

            except Exception as e:
                if isinstance(e, DataProcessingError):
                    raise
                raise DataProcessingError(
                    f"Failed to determine value range: {str(e)}",
                    operation="value_range_determination",
                ) from e

    def _create_processing_configuration(
        self, request: SingleRegionGridRequest
    ) -> ProcessingConfig:
        """
        Create processing configuration from request parameters.

        Converts string-based parameters from the request into strongly-typed
        enum values required by the data processing system. Handles metric type
        conversion (synapse_density vs cell_count) and soma side conversion
        (left/right/combined).

        Args:
            request: The single region grid request with string parameters

        Returns:
            ProcessingConfig object with properly typed enum values

        Raises:
            DataProcessingError: If configuration creation fails
        """
        with ErrorContext("processing_configuration_creation"):
            try:
                # Validate required fields
                if not hasattr(request, "metric_type") or request.metric_type is None:
                    raise DataProcessingError(
                        "Request missing required field: metric_type",
                        operation="processing_configuration_creation",
                    )

                # Convert metric type to enum with validation
                if request.metric_type == METRIC_SYNAPSE_DENSITY:
                    metric_enum = MetricType.SYNAPSE_DENSITY
                elif request.metric_type == METRIC_CELL_COUNT:
                    metric_enum = MetricType.CELL_COUNT
                else:
                    raise DataProcessingError(
                        f"Unknown metric type: {request.metric_type}. Expected: {METRIC_SYNAPSE_DENSITY} or {METRIC_CELL_COUNT}",
                        operation="processing_configuration_creation",
                        data_context={"metric_type": request.metric_type},
                    )

                # Convert soma_side to enum with validation
                if hasattr(request, "soma_side") and request.soma_side:
                    if hasattr(request.soma_side, "value"):
                        # It's already a SomaSide enum
                        soma_enum = request.soma_side
                    elif request.soma_side in ["left", "L"]:
                        soma_enum = SomaSide.LEFT
                    elif request.soma_side in ["right", "R"]:
                        soma_enum = SomaSide.RIGHT
                    elif request.soma_side in ["combined", "C"]:
                        soma_enum = SomaSide.COMBINED
                    else:
                        logger.warning(
                            f"Unknown soma_side: {request.soma_side}, defaulting to COMBINED"
                        )
                        soma_enum = SomaSide.COMBINED
                else:
                    soma_enum = SomaSide.COMBINED

                # Create configuration with validation
                config = ProcessingConfig(
                    metric_type=metric_enum,
                    soma_side=soma_enum,
                    region_name=getattr(request, "region_name", ""),
                    neuron_type=getattr(request, "neuron_type", ""),
                    output_format=getattr(request, "output_format", "svg"),
                )

                logger.debug(
                    f"Created processing configuration: metric={metric_enum}, side={soma_enum}"
                )
                return config

            except Exception as e:
                if isinstance(e, DataProcessingError):
                    raise
                raise DataProcessingError(
                    f"Failed to create processing configuration: {str(e)}",
                    operation="processing_configuration_creation",
                ) from e

    def _extract_layer_colors(
        self, processed_col, request: SingleRegionGridRequest
    ) -> List:
        """
        Extract layer colors from column data using structured ColumnData objects.
        """
        if processed_col.status == ColumnStatus.HAS_DATA:
            data_key = (request.region_name, processed_col.hex1, processed_col.hex2)
            data_col = request.data_map.get(data_key)

            if data_col and hasattr(data_col, "layers") and data_col.layers:
                if request.metric_type == METRIC_SYNAPSE_DENSITY:
                    # Extract synapse counts from layers
                    return [layer.synapse_count for layer in data_col.layers]
                elif request.metric_type == METRIC_CELL_COUNT:
                    # Extract neuron counts from layers
                    return [layer.neuron_count for layer in data_col.layers]
                else:
                    return processed_col.layer_colors
            else:
                return processed_col.layer_colors
        else:
            return []

    def _get_display_layer_name(self, region: str, layer_num: int) -> str:
        """Convert layer numbers to display names for specific regions."""
        if region == "LO":
            layer_mapping = {5: "5A", 6: "5B", 7: "6"}
            display_num = layer_mapping.get(layer_num, str(layer_num))
            return f"{region}{display_num}"
        else:
            return f"{region}{layer_num}"

    def _generate_tooltips_for_hexagons(
        self, hexagons: List[Dict], soma_side: str, metric_type: str, region: str
    ) -> List[Dict]:
        """
        Generate tooltips for hexagons using modern implementation.

        Args:
            hexagons: List of hexagon data dictionaries
            soma_side: Side identifier (converted to string)
            metric_type: Type of metric being displayed
            region: Region name

        Returns:
            List of hexagons with tooltip data added
        """
        from .constants import METRIC_SYNAPSE_DENSITY

        # Convert soma_side to string if it's an enum
        if hasattr(soma_side, "value"):
            soma_side_str = soma_side.value
        else:
            soma_side_str = str(soma_side)

        lbl_stat_for_zero = (
            TOOLTIP_SYNAPSE_LABEL
            if metric_type == METRIC_SYNAPSE_DENSITY
            else TOOLTIP_CELL_LABEL
        )

        processed_hexagons = []
        for hex_data in hexagons:
            status = hex_data.get("status", "has_data")
            hex1 = hex_data.get("hex1", "")
            hex2 = hex_data.get("hex2", "")
            value = hex_data.get("value", 0)
            layer_values = hex_data.get("layer_values") or []

            # Main tooltip
            if status == "not_in_region":
                tooltip = (
                    f"Column: {hex1}, {hex2}\n"
                    f"Column not identified in {region} ({soma_side_str})"
                )
            elif status == "no_data":
                tooltip = (
                    f"Column: {hex1}, {hex2}\n"
                    f"{lbl_stat_for_zero}: 0\n"
                    f"ROI: {region} ({soma_side_str})"
                )
            else:  # has_data
                tooltip = (
                    f"Column: {hex1}, {hex2}\n"
                    f"{lbl_stat_for_zero}: {int(value)}\n"
                    f"ROI: {region} ({soma_side_str})"
                )

            # Per-layer tooltips
            tooltip_layers = []
            for i, v in enumerate(layer_values, start=1):
                if status == "not_in_region":
                    layer_tip = (
                        f"Column: {hex1}, {hex2}\n"
                        f"Column not identified in {region} ({soma_side_str}) layer({i})"
                    )
                elif status == "no_data":
                    layer_tip = f"0\nROI: {self._get_display_layer_name(region, i)}"
                else:  # has_data
                    layer_tip = (
                        f"{int(v)}\nROI: {self._get_display_layer_name(region, i)}"
                    )
                tooltip_layers.append(layer_tip)

            processed_hex = hex_data.copy()
            processed_hex["tooltip"] = tooltip
            processed_hex["tooltip_layers"] = tooltip_layers
            processed_hexagons.append(processed_hex)

        return processed_hexagons

    def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics for the eyemap generator.

        This method now delegates to the PerformanceManager for centralized
        performance monitoring and statistics collection.

        Returns:
            Dictionary containing performance metrics, cache statistics, and memory usage
        """
        # Fallback to original implementation
        with ErrorContext("performance_statistics_collection"):
            try:
                if not self.performance_enabled:
                    return {"performance_monitoring": "disabled"}

                stats = {}

                if self.performance_monitor:
                    try:
                        stats["performance_summary"] = (
                            self.performance_monitor.get_performance_summary()
                        )
                        stats["operation_stats"] = (
                            self.performance_monitor.get_operation_stats()
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get performance monitor stats: {e}")
                        stats["performance_monitor_error"] = str(e)

                if self.memory_optimizer:
                    try:
                        stats["memory_usage_mb"] = (
                            self.memory_optimizer.get_memory_usage_mb()
                        )
                        stats["memory_pressure"] = (
                            self.memory_optimizer.is_memory_pressure()
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get memory stats: {e}")
                        stats["memory_optimizer_error"] = str(e)

                # Add cache statistics if available
                if hasattr(self, "optimizers") and self.optimizers:
                    cache_stats = {}
                    for name, optimizer in self.optimizers.items():
                        try:
                            if hasattr(optimizer, "cache_manager"):
                                cache_stats[name] = (
                                    optimizer.cache_manager.get_statistics()
                                )
                        except Exception as e:
                            logger.warning(f"Failed to get cache stats for {name}: {e}")
                            cache_stats[f"{name}_error"] = str(e)
                    stats["cache_statistics"] = cache_stats

                return stats

            except Exception as e:
                from .exceptions import PerformanceError

                raise PerformanceError(
                    f"Failed to collect performance statistics: {str(e)}"
                ) from e

    def clear_performance_caches(self) -> Dict[str, Union[int, str]]:
        """
        Clear all performance caches and return cleanup statistics.

        This method now delegates to the PerformanceManager for centralized
        cache management and cleanup operations.

        Returns:
            Dictionary with cache cleanup counts
        """
        # Fallback to original implementation
        with ErrorContext("performance_cache_clearing"):
            try:
                if not self.performance_enabled or not self.optimizers:
                    return {"message": "Performance optimization not enabled"}

                cleanup_counts = {}
                errors = []

                for name, optimizer in self.optimizers.items():
                    try:
                        if hasattr(optimizer, "cache_manager"):
                            cleanup_result = optimizer.cache_manager.cleanup_all()
                            cleanup_counts.update(
                                {f"{name}_{k}": v for k, v in cleanup_result.items()}
                            )
                    except Exception as e:
                        logger.warning(f"Failed to clear cache for {name}: {e}")
                        errors.append(f"{name}: {str(e)}")

                # Force garbage collection
                if self.memory_optimizer:
                    try:
                        gc_stats = self.memory_optimizer.force_garbage_collection()
                        cleanup_counts["garbage_collection"] = gc_stats
                    except Exception as e:
                        logger.warning(f"Failed to run garbage collection: {e}")
                        errors.append(f"garbage_collection: {str(e)}")

                if errors:
                    cleanup_counts["errors"] = errors

                logger.debug(
                    f"Cache cleanup completed with {len(cleanup_counts)} results"
                )
                return cleanup_counts

            except Exception as e:
                from .exceptions import PerformanceError

                raise PerformanceError(
                    f"Failed to clear performance caches: {str(e)}"
                ) from e

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """
        Optimize memory usage by delegating to the PerformanceManager.

        This method now uses the centralized PerformanceManager for
        memory optimization operations.

        Returns:
            Dictionary with optimization results
        """
        # Fallback to original implementation
        with ErrorContext("memory_optimization"):
            try:
                if not self.performance_enabled:
                    return {"message": "Performance optimization not enabled"}

                results = {}
                initial_memory = None

                # Get initial memory usage
                if self.memory_optimizer:
                    try:
                        initial_memory = self.memory_optimizer.get_memory_usage_mb()
                        results["memory_before_optimization"] = initial_memory
                    except Exception as e:
                        logger.warning(f"Failed to get initial memory usage: {e}")

                # Clear caches
                try:
                    cache_cleanup = self.clear_performance_caches()
                    results["cache_cleanup"] = cache_cleanup
                except Exception as e:
                    logger.warning(f"Cache cleanup failed: {e}")
                    results["cache_cleanup_error"] = str(e)

                # Force garbage collection
                if self.memory_optimizer:
                    try:
                        gc_results = self.memory_optimizer.force_garbage_collection()
                        results["garbage_collection"] = gc_results
                    except Exception as e:
                        logger.warning(f"Garbage collection failed: {e}")
                        results["garbage_collection_error"] = str(e)

                # Get updated memory usage
                if self.memory_optimizer:
                    try:
                        final_memory = self.memory_optimizer.get_memory_usage_mb()
                        results["memory_after_optimization"] = final_memory
                        if initial_memory is not None:
                            results["memory_savings_mb"] = initial_memory - final_memory
                    except Exception as e:
                        logger.warning(f"Failed to get final memory usage: {e}")

                logger.info("Memory optimization completed")
                return results

            except Exception as e:
                from .exceptions import PerformanceError

                raise PerformanceError(f"Memory optimization failed: {str(e)}") from e

    def _determine_mirror_side_with_context(
        self, soma_side: SomaSide, current_side: str = None
    ) -> str:
        """
        Determine if mirroring should be applied based on soma side.

        Args:
            soma_side: Soma side configuration
            current_side: Unused parameter (kept for compatibility)

        Returns:
            Mirror side string ('left' or 'right')
        """
        # For dedicated soma sides, use straightforward logic
        if soma_side in [SomaSide.RIGHT, SomaSide.R]:
            return "left"  # Apply mirroring for right soma side
        else:
            return "right"  # No mirroring for left soma side and combined mode
