"""
Validation Manager for Data Processing Module

This module provides comprehensive data validation functionality for the hexagon
grid generator data processing system. It validates column data, coordinates,
thresholds, and configuration parameters to ensure data integrity.
"""

import logging
from typing import List, Dict, Set, Tuple
from .data_structures import (
    ColumnData,
    ColumnCoordinate,
    ProcessingConfig,
    ValidationResult,
    MetricType,
    SomaSide,
    ColumnStatus,
    ThresholdData,
    MinMaxData,
)

logger = logging.getLogger(__name__)


class ValidationManager:
    """
    Manages validation of data processing inputs and outputs.

    This class provides comprehensive validation for all data structures
    used in the data processing pipeline, ensuring data integrity and
    providing detailed error reporting.
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the validation manager.

        Args:
            strict_mode: If True, validation will be more restrictive
        """
        self.strict_mode = strict_mode
        self.logger = logging.getLogger(__name__)

    def validate_column_data(self, column_data: List[ColumnData]) -> ValidationResult:
        """
        Validate a list of column data objects.

        Args:
            column_data: List of ColumnData objects to validate

        Returns:
            ValidationResult containing validation status and messages
        """
        result = ValidationResult(is_valid=True)

        if not column_data:
            result.add_warning("No column data provided for validation")
            return result

        seen_keys = set()

        for i, column in enumerate(column_data):
            try:
                # Validate individual column
                column_result = self._validate_single_column(column, i)

                # Merge results
                result.errors.extend(column_result.errors)
                result.warnings.extend(column_result.warnings)

                if not column_result.is_valid:
                    result.is_valid = False
                    result.rejected_count += 1
                else:
                    result.validated_count += 1

                # Check for duplicate keys (now includes side in key)
                key = column.key
                if key in seen_keys:
                    result.add_error(f"Duplicate column key found: {key}")
                seen_keys.add(key)

            except Exception as e:
                result.add_error(f"Exception validating column {i}: {str(e)}")
                result.rejected_count += 1

        self.logger.debug(f"Column data validation: {result.summary}")
        return result

    def _validate_single_column(
        self, column: ColumnData, index: int
    ) -> ValidationResult:
        """
        Validate a single column data object.

        Args:
            column: ColumnData object to validate
            index: Index of the column in the list (for error reporting)

        Returns:
            ValidationResult for this column
        """
        result = ValidationResult(is_valid=True)

        try:
            # Validate coordinate
            if not self._validate_coordinate(column.coordinate):
                result.add_error(
                    f"Column {index}: Invalid coordinate {column.coordinate}"
                )

            # Validate region
            if not column.region or not isinstance(column.region, str):
                result.add_error(f"Column {index}: Invalid region '{column.region}'")
            elif len(column.region.strip()) == 0:
                result.add_error(f"Column {index}: Empty region name")

            # Validate side
            valid_sides = ["L", "R"]
            if column.side not in valid_sides:
                result.add_error(
                    f"Column {index}: Invalid side '{column.side}', must be one of {valid_sides}"
                )

            # Validate numeric values
            if column.total_synapses < 0:
                result.add_error(
                    f"Column {index}: Negative total_synapses ({column.total_synapses})"
                )

            if column.neuron_count < 0:
                result.add_error(
                    f"Column {index}: Negative neuron_count ({column.neuron_count})"
                )

            # Validate layers
            layer_result = self._validate_layers(column.layers, index)
            result.errors.extend(layer_result.errors)
            result.warnings.extend(layer_result.warnings)

            # Cross-validation: check if layer totals match column totals
            if column.layers:
                layer_synapse_total = sum(
                    layer.synapse_count for layer in column.layers
                )
                layer_neuron_total = sum(layer.neuron_count for layer in column.layers)

                if self.strict_mode:
                    if layer_synapse_total != column.total_synapses:
                        result.add_warning(
                            f"Column {index}: Layer synapse total ({layer_synapse_total}) "
                            f"doesn't match column total ({column.total_synapses})"
                        )

                    if layer_neuron_total != column.neuron_count:
                        result.add_warning(
                            f"Column {index}: Layer neuron total ({layer_neuron_total}) "
                            f"doesn't match column total ({column.neuron_count})"
                        )

            # Validate status
            if not isinstance(column.status, ColumnStatus):
                result.add_error(f"Column {index}: Invalid status type")

        except Exception as e:
            result.add_error(f"Column {index}: Exception during validation: {str(e)}")

        return result

    def _validate_coordinate(self, coord: ColumnCoordinate) -> bool:
        """
        Validate a column coordinate.

        Args:
            coord: ColumnCoordinate to validate

        Returns:
            True if coordinate is valid
        """
        if not isinstance(coord, ColumnCoordinate):
            return False

        if not isinstance(coord.hex1, int) or not isinstance(coord.hex2, int):
            return False

        # Reasonable coordinate bounds (can be adjusted based on requirements)
        if abs(coord.hex1) > 1000 or abs(coord.hex2) > 1000:
            return False

        return True

    def _validate_layers(self, layers: List, index: int) -> ValidationResult:
        """
        Validate layer data for a column.

        Args:
            layers: List of LayerData objects
            index: Column index for error reporting

        Returns:
            ValidationResult for layers
        """
        result = ValidationResult(is_valid=True)

        if not layers:
            return result

        seen_indices = set()

        for i, layer in enumerate(layers):
            try:
                # Validate layer index
                if layer.layer_index < 0:
                    result.add_error(
                        f"Column {index}, Layer {i}: Negative layer_index ({layer.layer_index})"
                    )

                if layer.layer_index in seen_indices:
                    result.add_error(
                        f"Column {index}: Duplicate layer_index ({layer.layer_index})"
                    )
                seen_indices.add(layer.layer_index)

                # Validate counts
                if layer.synapse_count < 0:
                    result.add_error(
                        f"Column {index}, Layer {i}: Negative synapse_count ({layer.synapse_count})"
                    )

                if layer.neuron_count < 0:
                    result.add_error(
                        f"Column {index}, Layer {i}: Negative neuron_count ({layer.neuron_count})"
                    )

                # Validate value
                if not isinstance(layer.value, (int, float)):
                    result.add_error(f"Column {index}, Layer {i}: Invalid value type")
                elif layer.value < 0:
                    result.add_warning(
                        f"Column {index}, Layer {i}: Negative value ({layer.value})"
                    )

            except Exception as e:
                result.add_error(
                    f"Column {index}, Layer {i}: Exception during validation: {str(e)}"
                )

        return result

    def validate_processing_config(self, config: ProcessingConfig) -> ValidationResult:
        """
        Validate processing configuration.

        Args:
            config: ProcessingConfig to validate

        Returns:
            ValidationResult containing validation status
        """
        result = ValidationResult(is_valid=True)

        try:
            # Validate metric type
            if not isinstance(config.metric_type, MetricType):
                result.add_error(f"Invalid metric_type: {config.metric_type}")

            # Validate soma side
            if not isinstance(config.soma_side, SomaSide):
                result.add_error(f"Invalid soma_side: {config.soma_side}")

            # Validate region name
            if not config.region_name or not isinstance(config.region_name, str):
                result.add_error("Invalid region_name")
            elif len(config.region_name.strip()) == 0:
                result.add_error("Empty region_name")

            # Validate output format
            valid_formats = ["svg", "png"]
            if config.output_format not in valid_formats:
                result.add_error(
                    f"Invalid output_format '{config.output_format}', must be one of {valid_formats}"
                )

            # Validate precision
            if config.precision < 0:
                result.add_error(f"Invalid precision {config.precision}, must be >= 0")
            elif config.precision > 10:
                result.add_warning(
                    f"High precision value {config.precision} may affect performance"
                )

            # Validate neuron type if provided
            if config.neuron_type is not None and len(config.neuron_type.strip()) == 0:
                result.add_warning("Empty neuron_type provided")

        except Exception as e:
            result.add_error(f"Exception validating processing config: {str(e)}")

        return result

    def validate_threshold_data(self, thresholds: ThresholdData) -> ValidationResult:
        """
        Validate threshold data.

        Args:
            thresholds: ThresholdData to validate

        Returns:
            ValidationResult containing validation status
        """
        result = ValidationResult(is_valid=True)

        try:
            # Validate min/max values
            if thresholds.min_value >= thresholds.max_value:
                result.add_error(
                    f"min_value ({thresholds.min_value}) must be less than max_value ({thresholds.max_value})"
                )

            # Validate all_layers thresholds
            if thresholds.all_layers:
                if not self._validate_threshold_list(thresholds.all_layers):
                    result.add_error("Invalid all_layers threshold list")

                # Check if thresholds are within min/max range
                for i, threshold in enumerate(thresholds.all_layers):
                    if (
                        threshold < thresholds.min_value
                        or threshold > thresholds.max_value
                    ):
                        result.add_warning(
                            f"Threshold {i} ({threshold}) outside min/max range"
                        )

            # Validate layer-specific thresholds
            for layer_idx, layer_thresholds in thresholds.layers.items():
                if not isinstance(layer_idx, int) or layer_idx < 0:
                    result.add_error(f"Invalid layer index: {layer_idx}")

                if not self._validate_threshold_list(layer_thresholds):
                    result.add_error(f"Invalid threshold list for layer {layer_idx}")

        except Exception as e:
            result.add_error(f"Exception validating threshold data: {str(e)}")

        return result

    def _validate_threshold_list(self, thresholds: List[float]) -> bool:
        """
        Validate a list of threshold values.

        Args:
            thresholds: List of threshold values

        Returns:
            True if list is valid
        """
        if not thresholds:
            return True

        # Check if all values are numeric
        if not all(isinstance(t, (int, float)) for t in thresholds):
            return False

        # Check if values are in ascending order
        if not all(
            thresholds[i] <= thresholds[i + 1] for i in range(len(thresholds) - 1)
        ):
            return False

        return True


    def validate_region_columns_map(
        self, region_columns_map: Dict[str, Set[Tuple[int, int]]]
    ) -> ValidationResult:
        """
        Validate region columns mapping.

        Args:
            region_columns_map: Dictionary mapping region_side to coordinate sets

        Returns:
            ValidationResult containing validation status
        """
        result = ValidationResult(is_valid=True)

        try:
            if not region_columns_map:
                result.add_warning("Empty region_columns_map provided")
                return result

            for region_side, coords in region_columns_map.items():
                # Validate region_side format
                if not isinstance(region_side, str) or "_" not in region_side:
                    result.add_error(
                        f"Invalid region_side format: '{region_side}' (expected format: 'REGION_SIDE')"
                    )
                    continue

                parts = region_side.split("_")
                if len(parts) != 2:
                    result.add_error(
                        f"Invalid region_side format: '{region_side}' (expected format: 'REGION_SIDE')"
                    )
                    continue

                region, side = parts
                if not region or not side:
                    result.add_error(
                        f"Empty region or side in region_side: '{region_side}'"
                    )

                if side not in ["L", "R"]:
                    result.add_error(
                        f"Invalid side '{side}' in region_side: '{region_side}'"
                    )

                # Validate coordinates
                if not isinstance(coords, set):
                    result.add_error(
                        f"Region_side '{region_side}': coordinates must be a set"
                    )
                    continue

                for coord in coords:
                    if not isinstance(coord, tuple) or len(coord) != 2:
                        result.add_error(
                            f"Region_side '{region_side}': invalid coordinate format {coord}"
                        )
                        continue

                    hex1, hex2 = coord
                    if not isinstance(hex1, int) or not isinstance(hex2, int):
                        result.add_error(
                            f"Region_side '{region_side}': coordinate values must be integers {coord}"
                        )

        except Exception as e:
            result.add_error(f"Exception validating region_columns_map: {str(e)}")

        return result

    def validate_data_consistency(
        self,
        column_data: List[ColumnData],
        region_columns_map: Dict[str, Set[Tuple[int, int]]],
    ) -> ValidationResult:
        """
        Validate consistency between column data and region columns mapping.

        Args:
            column_data: List of ColumnData objects
            region_columns_map: Dictionary mapping region_side to coordinate sets

        Returns:
            ValidationResult containing validation status
        """
        result = ValidationResult(is_valid=True)

        try:
            # Build map of coordinates from column data
            column_coords = {}
            for column in column_data:
                region_side = f"{column.region}_{column.side}"
                if region_side not in column_coords:
                    column_coords[region_side] = set()
                column_coords[region_side].add(
                    (column.coordinate.hex1, column.coordinate.hex2)
                )

            # Check consistency - only warn, don't fail validation for missing/extra coordinates
            for region_side, expected_coords in region_columns_map.items():
                actual_coords = column_coords.get(region_side, set())

                # Check for missing coordinates in column data
                missing_in_data = expected_coords - actual_coords
                if missing_in_data and len(missing_in_data) > 0:
                    result.add_warning(
                        f"Region_side '{region_side}': {len(missing_in_data)} coordinates missing in column data"
                    )

                # Check for extra coordinates in column data
                extra_in_data = actual_coords - expected_coords
                if extra_in_data and len(extra_in_data) > 0:
                    result.add_warning(
                        f"Region_side '{region_side}': {len(extra_in_data)} extra coordinates in column data"
                    )

            # Also check for region_sides in column data that aren't in the map
            for region_side in column_coords:
                if region_side not in region_columns_map:
                    result.add_warning(
                        f"Column data contains region_side '{region_side}' not found in region_columns_map"
                    )

        except Exception as e:
            result.add_error(f"Exception validating data consistency: {str(e)}")

        return result
