"""
Threshold Calculator for Data Processing Module

This module provides functionality for calculating and managing thresholds used
in value-to-color mapping for hexagon grid visualizations. It handles both
global thresholds across all data and region-specific thresholds.
"""

import logging
from typing import List, Dict, Optional
import numpy as np
from .data_structures import (
    ColumnData,
    ThresholdData,
    MetricType,
    ValidationResult,
    MinMaxData,
)
from .validation_manager import ValidationManager

logger = logging.getLogger(__name__)


class ThresholdCalculator:
    """
    Calculates thresholds for value-to-color mapping in hexagon grid visualizations.

    This class provides methods for calculating both global and region-specific
    thresholds using various statistical methods including percentiles, quantiles,
    and standard deviation-based approaches.
    """

    def __init__(self, validation_manager: Optional[ValidationManager] = None):
        """
        Initialize the threshold calculator.

        Args:
            validation_manager: Optional validation manager for input validation
        """
        self.validation_manager = validation_manager or ValidationManager()
        self.logger = logging.getLogger(__name__)

    def calculate_thresholds(
        self,
        column_data: List[ColumnData],
        metric_type: MetricType,
        num_thresholds: int = 5,
        method: str = "percentile",
        exclude_zeros: bool = True,
    ) -> ThresholdData:
        """
        Calculate thresholds for the given column data and metric type.

        Args:
            column_data: List of column data to analyze
            metric_type: Type of metric to calculate thresholds for
            num_thresholds: Number of threshold values to generate
            method: Method to use ('percentile', 'quantile', 'equal', 'std_dev')
            exclude_zeros: Whether to exclude zero values from calculations

        Returns:
            ThresholdData containing calculated thresholds
        """
        # Validate inputs
        validation_result = self.validation_manager.validate_column_data(column_data)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid column data: {validation_result.errors}")

        if num_thresholds < 2:
            raise ValueError("num_thresholds must be at least 2")

        # Extract values for the specified metric
        values = self._extract_metric_values(column_data, metric_type, exclude_zeros)

        if not values:
            self.logger.warning(f"No values found for metric {metric_type}")
            return ThresholdData(min_value=0.0, max_value=1.0)

        # Calculate global thresholds
        all_thresholds = self._calculate_threshold_values(
            values, num_thresholds, method
        )

        # Calculate layer-specific thresholds
        layer_thresholds = self._calculate_layer_thresholds(
            column_data, metric_type, num_thresholds, method, exclude_zeros
        )

        # Determine min/max values
        min_value = float(min(values)) if values else 0.0
        max_value = float(max(values)) if values else 1.0

        return ThresholdData(
            all_layers=all_thresholds,
            layers=layer_thresholds,
            min_value=min_value,
            max_value=max_value,
        )

    def calculate_min_max_data(
        self, column_data: List[ColumnData], regions: Optional[List[str]] = None
    ) -> MinMaxData:
        """
        Calculate min/max values for normalization across regions and metrics.

        Args:
            column_data: List of column data to analyze
            regions: Optional list of regions to include (default: all regions)

        Returns:
            MinMaxData containing min/max values for different metrics and regions
        """
        # Validate inputs
        validation_result = self.validation_manager.validate_column_data(column_data)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid column data: {validation_result.errors}")

        # Organize data by region
        region_data = self._organize_data_by_region(column_data, regions)

        # Calculate global min/max values
        all_syn_values = []
        all_cell_values = []

        for column in column_data:
            if column.total_synapses > 0:
                all_syn_values.append(column.total_synapses)
            if column.neuron_count > 0:
                all_cell_values.append(column.neuron_count)

        global_min_syn = float(min(all_syn_values)) if all_syn_values else 0.0
        global_max_syn = float(max(all_syn_values)) if all_syn_values else 1.0
        global_min_cells = float(min(all_cell_values)) if all_cell_values else 0.0
        global_max_cells = float(max(all_cell_values)) if all_cell_values else 1.0

        # Calculate region-specific min/max values
        min_syn_region = {}
        max_syn_region = {}
        min_cells_region = {}
        max_cells_region = {}

        for region, columns in region_data.items():
            syn_values = [
                col.total_synapses for col in columns if col.total_synapses > 0
            ]
            cell_values = [col.neuron_count for col in columns if col.neuron_count > 0]

            min_syn_region[region] = (
                float(min(syn_values)) if syn_values else global_min_syn
            )
            max_syn_region[region] = (
                float(max(syn_values)) if syn_values else global_max_syn
            )
            min_cells_region[region] = (
                float(min(cell_values)) if cell_values else global_min_cells
            )
            max_cells_region[region] = (
                float(max(cell_values)) if cell_values else global_max_cells
            )

        return MinMaxData(
            min_syn_region=min_syn_region,
            max_syn_region=max_syn_region,
            min_cells_region=min_cells_region,
            max_cells_region=max_cells_region,
            global_min_syn=global_min_syn,
            global_max_syn=global_max_syn,
            global_min_cells=global_min_cells,
            global_max_cells=global_max_cells,
        )


    def _extract_metric_values(
        self,
        column_data: List[ColumnData],
        metric_type: MetricType,
        exclude_zeros: bool = True,
    ) -> List[float]:
        """
        Extract metric values from column data.

        Args:
            column_data: List of column data
            metric_type: Type of metric to extract
            exclude_zeros: Whether to exclude zero values

        Returns:
            List of extracted metric values
        """
        values = []

        for column in column_data:
            if metric_type == MetricType.SYNAPSE_DENSITY:
                value = float(column.total_synapses)
            elif metric_type == MetricType.CELL_COUNT:
                value = float(column.neuron_count)
            else:
                continue

            if exclude_zeros and value == 0:
                continue

            values.append(value)

        return values

    def _calculate_threshold_values(
        self, values: List[float], num_thresholds: int, method: str
    ) -> List[float]:
        """
        Calculate threshold values using the specified method.

        Args:
            values: List of values to analyze
            num_thresholds: Number of thresholds to generate
            method: Calculation method

        Returns:
            List of threshold values
        """
        if not values:
            return []

        values_array = np.array(values)

        if method == "percentile":
            percentiles = np.linspace(0, 100, num_thresholds)
            thresholds = [float(np.percentile(values_array, p)) for p in percentiles]
        elif method == "quantile":
            quantiles = np.linspace(0, 1, num_thresholds)
            thresholds = [float(np.quantile(values_array, q)) for q in quantiles]
        elif method == "equal":
            min_val, max_val = values_array.min(), values_array.max()
            thresholds = [
                float(val) for val in np.linspace(min_val, max_val, num_thresholds)
            ]
        elif method == "std_dev":
            mean_val = values_array.mean()
            std_val = values_array.std()
            # Create thresholds at mean ± n*std_dev
            factors = np.linspace(-2, 2, num_thresholds)
            thresholds = [float(mean_val + factor * std_val) for factor in factors]
            # Clamp to data range
            min_val, max_val = values_array.min(), values_array.max()
            thresholds = [max(min_val, min(max_val, t)) for t in thresholds]
        else:
            raise ValueError(f"Unknown threshold calculation method: {method}")

        # Remove duplicates and sort
        thresholds = sorted(list(set(thresholds)))

        return thresholds

    def _calculate_layer_thresholds(
        self,
        column_data: List[ColumnData],
        metric_type: MetricType,
        num_thresholds: int,
        method: str,
        exclude_zeros: bool,
    ) -> Dict[int, List[float]]:
        """
        Calculate layer-specific thresholds.

        Args:
            column_data: List of column data
            metric_type: Type of metric to calculate thresholds for
            num_thresholds: Number of thresholds per layer
            method: Calculation method
            exclude_zeros: Whether to exclude zero values

        Returns:
            Dictionary mapping layer indices to threshold lists
        """
        layer_thresholds = {}

        # Organize values by layer
        layer_values = {}
        for column in column_data:
            for layer in column.layers:
                layer_idx = layer.layer_index
                if layer_idx not in layer_values:
                    layer_values[layer_idx] = []

                if metric_type == MetricType.SYNAPSE_DENSITY:
                    value = float(layer.synapse_count)
                elif metric_type == MetricType.CELL_COUNT:
                    value = float(layer.neuron_count)
                else:
                    continue

                if exclude_zeros and value == 0:
                    continue

                layer_values[layer_idx].append(value)

        # Calculate thresholds for each layer
        for layer_idx, values in layer_values.items():
            if values:
                thresholds = self._calculate_threshold_values(
                    values, num_thresholds, method
                )
                layer_thresholds[layer_idx] = thresholds

        return layer_thresholds

    def _organize_data_by_region(
        self, column_data: List[ColumnData], regions: Optional[List[str]] = None
    ) -> Dict[str, List[ColumnData]]:
        """
        Organize column data by region.

        Args:
            column_data: List of column data
            regions: Optional list of regions to include

        Returns:
            Dictionary mapping regions to column data lists
        """
        region_data = {}

        for column in column_data:
            region = column.region
            if regions is not None and region not in regions:
                continue

            if region not in region_data:
                region_data[region] = []
            region_data[region].append(column)

        return region_data

    def _calculate_balanced_thresholds(
        self, values_array: np.ndarray, num_bins: int = 5
    ) -> List[float]:
        """
        Calculate thresholds that create balanced bins with equal data points.

        Args:
            values_array: Array of values
            num_bins: Number of bins to create

        Returns:
            List of threshold values
        """
        percentiles = np.linspace(0, 100, num_bins + 1)
        thresholds = [float(np.percentile(values_array, p)) for p in percentiles]
        return thresholds

    def _calculate_log_scale_thresholds(
        self, values_array: np.ndarray, num_bins: int = 5
    ) -> List[float]:
        """
        Calculate logarithmic scale thresholds for highly skewed data.

        Args:
            values_array: Array of values
            num_bins: Number of bins to create

        Returns:
            List of threshold values
        """
        # Add small value to handle zeros
        log_values = np.log10(values_array + 1e-10)
        log_min, log_max = log_values.min(), log_values.max()

        log_thresholds = np.linspace(log_min, log_max, num_bins + 1)
        thresholds = [float(10**log_t - 1e-10) for log_t in log_thresholds]

        # Ensure thresholds are within original data range
        min_val, max_val = values_array.min(), values_array.max()
        thresholds = [max(min_val, min(max_val, t)) for t in thresholds]

        return thresholds

    def _calculate_data_driven_thresholds(
        self, values_array: np.ndarray
    ) -> List[float]:
        """
        Calculate thresholds based on data distribution characteristics.

        Args:
            values_array: Array of values

        Returns:
            List of threshold values
        """
        # Use statistical measures to determine thresholds
        q25 = float(np.percentile(values_array, 25))
        q50 = float(np.percentile(values_array, 50))
        q75 = float(np.percentile(values_array, 75))
        min_val = float(values_array.min())
        max_val = float(values_array.max())

        # Create thresholds based on quartiles and extremes
        thresholds = [min_val, q25, q50, q75, max_val]

        # Add intermediate values if range is large
        if max_val > q75 * 2:
            # Add threshold between q75 and max
            high_threshold = q75 + (max_val - q75) * 0.5
            thresholds.insert(-1, float(high_threshold))

        if q25 > min_val * 2:
            # Add threshold between min and q25
            low_threshold = min_val + (q25 - min_val) * 0.5
            thresholds.insert(1, float(low_threshold))

        return sorted(list(set(thresholds)))

    def validate_thresholds(self, thresholds: ThresholdData) -> ValidationResult:
        """
        Validate calculated thresholds.

        Args:
            thresholds: ThresholdData to validate

        Returns:
            ValidationResult containing validation status
        """
        return self.validation_manager.validate_threshold_data(thresholds)


    def _score_threshold_distribution(
        self, values_array: np.ndarray, thresholds: List[float]
    ) -> float:
        """
        Score threshold distribution based on balance and coverage.

        Args:
            values_array: Array of values
            thresholds: List of threshold values

        Returns:
            Score (lower is better)
        """
        if len(thresholds) < 2:
            return float("inf")

        # Count values in each bin
        bin_counts = np.histogram(values_array, bins=thresholds)[0]

        # Calculate balance score (lower variance is better)
        if len(bin_counts) > 1:
            balance_score = np.var(bin_counts)
        else:
            balance_score = 0

        # Calculate coverage score (prefer using full data range)
        data_range = values_array.max() - values_array.min()
        threshold_range = max(thresholds) - min(thresholds)

        if data_range > 0:
            coverage_score = 1.0 - (threshold_range / data_range)
        else:
            coverage_score = 0

        # Combine scores (balance is more important)
        total_score = balance_score + coverage_score * 100

        return total_score
