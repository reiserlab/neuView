"""
Metric Calculator for Data Processing Module

This module provides functionality for calculating various metrics and values
used in hexagon grid visualizations. It handles metric extraction, normalization,
and transformation operations for different types of column data.
"""

import logging
import math
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from .data_structures import ColumnData, MetricType, MinMaxData
from .validation_manager import ValidationManager

logger = logging.getLogger(__name__)


class MetricCalculator:
    """
    Calculates metrics and values for hexagon grid visualizations.

    This class provides methods for extracting, normalizing, and transforming
    metric values from column data. It supports various metric types and
    normalization strategies.
    """

    def __init__(self, validation_manager: Optional[ValidationManager] = None):
        """
        Initialize the metric calculator.

        Args:
            validation_manager: Optional validation manager for input validation
        """
        self.validation_manager = validation_manager or ValidationManager()
        self.logger = logging.getLogger(__name__)

    def calculate_metric_value(
        self, column: ColumnData, metric_type: MetricType
    ) -> float:
        """
        Calculate the primary metric value for a column.

        Args:
            column: ColumnData to extract metric from
            metric_type: Type of metric to calculate

        Returns:
            Calculated metric value
        """
        if metric_type == MetricType.SYNAPSE_DENSITY:
            return float(column.total_synapses)
        elif metric_type == MetricType.CELL_COUNT:
            return float(column.neuron_count)
        else:
            raise ValueError(f"Unknown metric type: {metric_type}")

    def calculate_layer_values(
        self, column: ColumnData, metric_type: MetricType
    ) -> List[float]:
        """
        Calculate metric values for each layer in a column.

        Args:
            column: ColumnData to extract layer metrics from
            metric_type: Type of metric to calculate

        Returns:
            List of metric values for each layer
        """
        layer_values = []

        for layer in column.layers:
            if metric_type == MetricType.SYNAPSE_DENSITY:
                value = float(layer.synapse_count)
            elif metric_type == MetricType.CELL_COUNT:
                value = float(layer.neuron_count)
            else:
                value = 0.0

            layer_values.append(value)

        return layer_values

    def normalize_value(
        self,
        value: float,
        min_value: float,
        max_value: float,
        target_range: Tuple[float, float] = (0.0, 1.0),
    ) -> float:
        """
        Normalize a value to a target range.

        Args:
            value: Value to normalize
            min_value: Minimum value in the source range
            max_value: Maximum value in the source range
            target_range: Target range for normalization

        Returns:
            Normalized value
        """
        if max_value <= min_value:
            return target_range[0]

        # Normalize to 0-1 first
        normalized = (value - min_value) / (max_value - min_value)

        # Scale to target range
        target_min, target_max = target_range
        scaled = target_min + normalized * (target_max - target_min)

        # Clamp to target range
        return max(target_min, min(target_max, scaled))







    def _calculate_skewness(self, values: np.ndarray) -> float:
        """Calculate skewness of a distribution."""
        if len(values) < 3:
            return 0.0

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return 0.0

        skewness = np.mean(((values - mean) / std) ** 3)
        return float(skewness)

    def _calculate_kurtosis(self, values: np.ndarray) -> float:
        """Calculate kurtosis of a distribution."""
        if len(values) < 4:
            return 0.0

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return 0.0

        kurtosis = np.mean(((values - mean) / std) ** 4) - 3
        return float(kurtosis)

    def _calculate_entropy(self, proportions: List[float]) -> float:
        """Calculate Shannon entropy."""
        entropy = 0.0
        for p in proportions:
            if p > 0:
                entropy -= p * math.log(p)
        return entropy

    def _calculate_gini_coefficient(self, values: List[float]) -> float:
        """Calculate Gini coefficient for inequality measurement."""
        if not values or all(v == 0 for v in values):
            return 0.0

        sorted_values = sorted([v for v in values if v >= 0])
        n = len(sorted_values)
        total = sum(sorted_values)

        if total == 0:
            return 0.0

        gini = (2 * np.sum((np.arange(1, n + 1) * sorted_values))) / (n * total) - (
            n + 1
        ) / n

        return float(gini)

    def _classify_layer_pattern(self, values: List[float]) -> str:
        """Classify the pattern of values across layers."""
        if not values or len(values) < 2:
            return "uniform"

        # Normalize values
        total = sum(values)
        if total == 0:
            return "empty"

        proportions = [v / total for v in values]
        max_prop = max(proportions)

        # Classification thresholds
        if max_prop > 0.8:
            return "concentrated"
        elif max_prop > 0.6:
            return "skewed"
        elif all(0.1 <= p <= 0.4 for p in proportions):
            return "uniform"
        else:
            return "distributed"


