"""
Column Data Manager for Data Processing Module

This module provides functionality for organizing, filtering, and managing
column data used in hexagon grid visualizations. It handles data organization
by sides, regions, and coordinates, as well as data validation and merging.
"""

import logging
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
from .data_structures import (
    ColumnData,
    ColumnCoordinate,
    ColumnStatus,
    MetricType,
    SomaSide,
    RegionColumnsMap,
    ColumnDataMap,
)
from .validation_manager import ValidationManager

logger = logging.getLogger(__name__)


class ColumnDataManager:
    """
    Manages organization and transformation of column data for visualization.

    This class provides methods for organizing column data by region and side,
    filtering data based on various criteria, and transforming raw column data
    into formats suitable for visualization processing.
    """

    def __init__(self, validation_manager: Optional[ValidationManager] = None):
        """
        Initialize the column data manager.

        Args:
            validation_manager: Optional validation manager for data validation
        """
        self.validation_manager = validation_manager or ValidationManager()
        self.logger = logging.getLogger(__name__)

    def organize_structured_data_by_side(
        self, column_data: List[ColumnData], soma_side: SomaSide
    ) -> Dict[str, Dict[Tuple, ColumnData]]:
        """
        Organize ColumnData objects by side using modern structured approach.

        Args:
            column_data: List of ColumnData objects
            soma_side: Side specification as SomaSide enum

        Returns:
            Dictionary mapping sides to data maps with ColumnData objects

        Raises:
            ValueError: If invalid soma_side or no data for specified side
            TypeError: If soma_side is not a SomaSide enum
        """
        # Enforce enum validation
        if not isinstance(soma_side, SomaSide):
            raise TypeError(f"soma_side must be a SomaSide enum, got {type(soma_side)}")

        if not column_data:
            self.logger.debug("No column data provided for organization")
            return {}

        data_maps = {}

        if soma_side == SomaSide.COMBINED:
            # For combined sides, create separate data maps for L and R
            data_maps["L"] = {}
            data_maps["R"] = {}

            for col in column_data:
                if col.side in ["L", "R"]:
                    key = (col.region, col.coordinate.hex1, col.coordinate.hex2)
                    data_maps[col.side][key] = col
        else:
            # Determine target side from soma_side specification
            if soma_side in [SomaSide.LEFT, SomaSide.L]:
                target_side = "L"
            elif soma_side in [SomaSide.RIGHT, SomaSide.R]:
                target_side = "R"
            else:
                raise ValueError(f"Invalid soma_side specification: {soma_side}")

            data_maps[target_side] = {}
            matching_columns = [col for col in column_data if col.side == target_side]

            if not matching_columns:
                self.logger.debug(
                    f"No columns found for side {target_side} (may be normal for this neuron type)"
                )

            for col in matching_columns:
                key = (col.region, col.coordinate.hex1, col.coordinate.hex2)
                data_maps[target_side][key] = col

        self.logger.debug(
            f"Organized {len(column_data)} columns into {len(data_maps)} side maps"
        )
        return data_maps






    def determine_column_status(
        self,
        coordinate: ColumnCoordinate,
        region: str,
        region_column_coords: Set[Tuple[int, int]],
        data_map: ColumnDataMap,
        other_regions_coords: Optional[Set[Tuple[int, int]]] = None,
    ) -> ColumnStatus:
        """
        Determine the status of a column based on data availability.

        Args:
            coordinate: Column coordinate to check
            region: Target region name
            region_column_coords: Set of coordinates in the current region
            data_map: Dictionary mapping keys to column data
            other_regions_coords: Optional set of coordinates in other regions

        Returns:
            ColumnStatus indicating the column's status
        """
        coord_tuple = coordinate.to_tuple()
        data_key = (region, coordinate.hex1, coordinate.hex2)

        # Check if column exists in current region
        if coord_tuple in region_column_coords:
            if data_key in data_map:
                return ColumnStatus.HAS_DATA
            else:
                return ColumnStatus.NO_DATA
        elif other_regions_coords and coord_tuple in other_regions_coords:
            return ColumnStatus.NOT_IN_REGION
        else:
            return ColumnStatus.EXCLUDED






    def validate_data_consistency(self, columns: List[ColumnData]) -> Dict[str, Any]:
        """
        Validate consistency of column data.

        Args:
            columns: List of ColumnData to validate

        Returns:
            Dictionary containing validation results
        """
        validation_results = {
            "is_consistent": True,
            "issues": [],
            "warnings": [],
            "statistics": {},
        }

        # Check for duplicate coordinates
        seen_coords = set()
        duplicates = set()

        for column in columns:
            coord = column.coordinate.to_tuple()
            if coord in seen_coords:
                duplicates.add(coord)
                validation_results["is_consistent"] = False
            seen_coords.add(coord)

        if duplicates:
            validation_results["issues"].append(
                f"Duplicate coordinates found: {duplicates}"
            )

        # Check for missing layer data
        columns_with_layers = sum(1 for col in columns if col.layers)
        columns_without_layers = len(columns) - columns_with_layers

        if columns_without_layers > 0:
            validation_results["warnings"].append(
                f"{columns_without_layers} columns have no layer data"
            )

        # Check for data consistency within columns
        for column in columns:
            layer_syn_total = sum(layer.synapse_count for layer in column.layers)
            layer_neu_total = sum(layer.neuron_count for layer in column.layers)

            if layer_syn_total != column.total_synapses and column.layers:
                validation_results["warnings"].append(
                    f"Column {column.key}: layer synapse total mismatch"
                )

            if layer_neu_total != column.neuron_count and column.layers:
                validation_results["warnings"].append(
                    f"Column {column.key}: layer neuron total mismatch"
                )

        # Calculate statistics
        validation_results["statistics"] = {
            "total_columns": len(columns),
            "columns_with_layers": columns_with_layers,
            "columns_without_layers": columns_without_layers,
            "duplicate_count": len(duplicates),
            "regions": len(set(col.region for col in columns)),
            "sides": len(set(col.side for col in columns)),
        }

        return validation_results

    def _sum_columns(self, col1: ColumnData, col2: ColumnData) -> ColumnData:
        """
        Sum two columns' numeric values.

        Args:
            col1: First column
            col2: Second column

        Returns:
            ColumnData with summed values
        """
        from .data_structures import LayerData

        # Sum totals
        total_synapses = col1.total_synapses + col2.total_synapses
        neuron_count = col1.neuron_count + col2.neuron_count

        # Sum layers
        merged_layers = []
        max_layers = max(len(col1.layers), len(col2.layers))

        for i in range(max_layers):
            syn1 = col1.layers[i].synapse_count if i < len(col1.layers) else 0
            syn2 = col2.layers[i].synapse_count if i < len(col2.layers) else 0
            neu1 = col1.layers[i].neuron_count if i < len(col1.layers) else 0
            neu2 = col2.layers[i].neuron_count if i < len(col2.layers) else 0

            layer = LayerData(
                layer_index=i, synapse_count=syn1 + syn2, neuron_count=neu1 + neu2
            )
            merged_layers.append(layer)

        return ColumnData(
            coordinate=col1.coordinate,
            region=col1.region,
            side=col1.side,
            total_synapses=total_synapses,
            neuron_count=neuron_count,
            layers=merged_layers,
        )

    def _average_columns(self, col1: ColumnData, col2: ColumnData) -> ColumnData:
        """
        Average two columns' numeric values.

        Args:
            col1: First column
            col2: Second column

        Returns:
            ColumnData with averaged values
        """
        from .data_structures import LayerData

        # Average totals
        total_synapses = (col1.total_synapses + col2.total_synapses) // 2
        neuron_count = (col1.neuron_count + col2.neuron_count) // 2

        # Average layers
        merged_layers = []
        max_layers = max(len(col1.layers), len(col2.layers))

        for i in range(max_layers):
            syn1 = col1.layers[i].synapse_count if i < len(col1.layers) else 0
            syn2 = col2.layers[i].synapse_count if i < len(col2.layers) else 0
            neu1 = col1.layers[i].neuron_count if i < len(col1.layers) else 0
            neu2 = col2.layers[i].neuron_count if i < len(col2.layers) else 0

            layer = LayerData(
                layer_index=i,
                synapse_count=(syn1 + syn2) // 2,
                neuron_count=(neu1 + neu2) // 2,
            )
            merged_layers.append(layer)

        return ColumnData(
            coordinate=col1.coordinate,
            region=col1.region,
            side=col1.side,
            total_synapses=total_synapses,
            neuron_count=neuron_count,
            layers=merged_layers,
        )
