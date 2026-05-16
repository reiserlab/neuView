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

    def calculate_normalized_values(
        self,
        columns: List[ColumnData],
        metric_type: MetricType,
        min_max_data: Optional[MinMaxData] = None,
        region: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Calculate normalized values for a list of columns.

        Args:
            columns: List of ColumnData to normalize
            metric_type: Type of metric to normalize
            min_max_data: Optional MinMaxData for normalization bounds
            region: Optional region name for region-specific normalization

        Returns:
            Dictionary mapping column keys to normalized values
        """
        normalized_values = {}

        if not columns:
            return normalized_values

        # Determine normalization bounds
        if min_max_data and region:
            min_value = min_max_data.get_min_for_metric(metric_type, region)
            max_value = min_max_data.get_max_for_metric(metric_type, region)
        else:
            # Calculate bounds from provided data
            values = [self.calculate_metric_value(col, metric_type) for col in columns]
            values = [
                v for v in values if v > 0
            ]  # Exclude zeros for better normalization
            min_value = min(values) if values else 0.0
            max_value = max(values) if values else 1.0

        # Normalize each column
        for column in columns:
            value = self.calculate_metric_value(column, metric_type)
            normalized = self.normalize_value(value, min_value, max_value)
            normalized_values[column.key] = normalized

        return normalized_values


    def calculate_statistical_metrics(
        self, columns: List[ColumnData], metric_type: MetricType
    ) -> Dict[str, float]:
        """
        Calculate statistical metrics across a collection of columns.

        Args:
            columns: List of ColumnData to analyze
            metric_type: Type of metric to calculate statistics for

        Returns:
            Dictionary containing statistical metrics
        """
        if not columns:
            return {}

        # Extract values
        values = []
        for column in columns:
            value = self.calculate_metric_value(column, metric_type)
            if value > 0:  # Exclude zeros for statistical calculations
                values.append(value)

        if not values:
            return {}

        values_array = np.array(values)

        metrics = {
            "count": len(values),
            "mean": float(np.mean(values_array)),
            "median": float(np.median(values_array)),
            "std": float(np.std(values_array)),
            "variance": float(np.var(values_array)),
            "min": float(np.min(values_array)),
            "max": float(np.max(values_array)),
            "q25": float(np.percentile(values_array, 25)),
            "q75": float(np.percentile(values_array, 75)),
            "skewness": self._calculate_skewness(values_array),
            "kurtosis": self._calculate_kurtosis(values_array),
        }

        # Additional derived metrics
        metrics["range"] = metrics["max"] - metrics["min"]
        metrics["iqr"] = metrics["q75"] - metrics["q25"]
        metrics["cv"] = metrics["std"] / metrics["mean"] if metrics["mean"] > 0 else 0.0

        return metrics

    def calculate_percentile_ranks(
        self, columns: List[ColumnData], metric_type: MetricType
    ) -> Dict[str, float]:
        """
        Calculate percentile ranks for column values.

        Args:
            columns: List of ColumnData to rank
            metric_type: Type of metric to rank

        Returns:
            Dictionary mapping column keys to percentile ranks (0-100)
        """
        if not columns:
            return {}

        # Extract values and create mapping
        values = []
        column_values = {}

        for column in columns:
            value = self.calculate_metric_value(column, metric_type)
            values.append(value)
            column_values[column.key] = value

        values_array = np.array(values)
        percentile_ranks = {}

        for key, value in column_values.items():
            # Calculate percentile rank
            rank = (np.sum(values_array <= value) / len(values_array)) * 100
            percentile_ranks[key] = float(rank)

        return percentile_ranks

    def calculate_layer_distribution_metrics(
        self, column: ColumnData
    ) -> Dict[str, Any]:
        """
        Calculate metrics describing the distribution of values across layers.

        Args:
            column: ColumnData to analyze

        Returns:
            Dictionary containing layer distribution metrics
        """
        metrics = {}

        if not column.layers:
            return metrics

        synapse_counts = [layer.synapse_count for layer in column.layers]
        neuron_counts = [layer.neuron_count for layer in column.layers]

        # Calculate concentration metrics
        total_synapses = sum(synapse_counts)
        total_neurons = sum(neuron_counts)

        if total_synapses > 0:
            synapse_proportions = [count / total_synapses for count in synapse_counts]
            metrics["synapse_entropy"] = self._calculate_entropy(synapse_proportions)
            metrics["synapse_gini"] = self._calculate_gini_coefficient(synapse_counts)
        else:
            metrics["synapse_entropy"] = 0.0
            metrics["synapse_gini"] = 0.0

        if total_neurons > 0:
            neuron_proportions = [count / total_neurons for count in neuron_counts]
            metrics["neuron_entropy"] = self._calculate_entropy(neuron_proportions)
            metrics["neuron_gini"] = self._calculate_gini_coefficient(neuron_counts)
        else:
            metrics["neuron_entropy"] = 0.0
            metrics["neuron_gini"] = 0.0

        # Effective number of layers (Shannon diversity)
        if total_synapses > 0:
            metrics["effective_synapse_layers"] = math.exp(metrics["synapse_entropy"])
        else:
            metrics["effective_synapse_layers"] = 0.0

        if total_neurons > 0:
            metrics["effective_neuron_layers"] = math.exp(metrics["neuron_entropy"])
        else:
            metrics["effective_neuron_layers"] = 0.0

        # Layer activity patterns
        metrics["synapse_layer_pattern"] = self._classify_layer_pattern(synapse_counts)
        metrics["neuron_layer_pattern"] = self._classify_layer_pattern(neuron_counts)

        return metrics

    def calculate_relative_metrics(
        self,
        column: ColumnData,
        reference_columns: List[ColumnData],
        metric_type: MetricType,
    ) -> Dict[str, float]:
        """
        Calculate metrics relative to a reference set of columns.

        Args:
            column: ColumnData to calculate relative metrics for
            reference_columns: List of reference columns
            metric_type: Type of metric to compare

        Returns:
            Dictionary containing relative metrics
        """
        metrics = {}

        if not reference_columns:
            return metrics

        # Calculate reference statistics
        ref_values = [
            self.calculate_metric_value(col, metric_type) for col in reference_columns
        ]
        ref_values = [v for v in ref_values if v > 0]

        if not ref_values:
            return metrics

        ref_mean = np.mean(ref_values)
        ref_std = np.std(ref_values)
        ref_median = np.median(ref_values)

        # Calculate column value
        column_value = self.calculate_metric_value(column, metric_type)

        # Relative metrics
        metrics["relative_to_mean"] = (column_value / ref_mean) if ref_mean > 0 else 0.0
        metrics["relative_to_median"] = (
            (column_value / ref_median) if ref_median > 0 else 0.0
        )

        # Z-score
        if ref_std > 0:
            metrics["z_score"] = (column_value - ref_mean) / ref_std
        else:
            metrics["z_score"] = 0.0

        # Percentile rank within reference
        rank = (np.sum(np.array(ref_values) <= column_value) / len(ref_values)) * 100
        metrics["percentile_rank"] = float(rank)

        return metrics

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

    def calculate_column_similarity(
        self, column1: ColumnData, column2: ColumnData, metric_type: MetricType
    ) -> float:
        """
        Calculate similarity between two columns based on their layer patterns.

        Args:
            column1: First column to compare
            column2: Second column to compare
            metric_type: Type of metric to compare

        Returns:
            Similarity score between 0 and 1
        """
        # Extract layer values
        values1 = self.calculate_layer_values(column1, metric_type)
        values2 = self.calculate_layer_values(column2, metric_type)

        # Pad to same length
        max_len = max(len(values1), len(values2))
        values1.extend([0.0] * (max_len - len(values1)))
        values2.extend([0.0] * (max_len - len(values2)))

        if not values1 or not values2:
            return 0.0

        # Normalize to unit vectors
        norm1 = np.linalg.norm(values1)
        norm2 = np.linalg.norm(values2)

        if norm1 == 0 or norm2 == 0:
            return 1.0 if norm1 == norm2 else 0.0

        normalized1 = np.array(values1) / norm1
        normalized2 = np.array(values2) / norm2

        # Calculate cosine similarity
        similarity = float(np.dot(normalized1, normalized2))

        # Ensure result is between 0 and 1
        return max(0.0, min(1.0, similarity))

    def validate_metric_results(self, metrics: Dict[str, Any]) -> bool:
        """
        Validate calculated metric results.

        Args:
            metrics: Dictionary of calculated metrics

        Returns:
            True if metrics are valid
        """
        try:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    if math.isnan(value) or math.isinf(value):
                        self.logger.warning(f"Invalid metric value for {key}: {value}")
                        return False
                elif isinstance(value, (list, tuple)):
                    for item in value:
                        if isinstance(item, (int, float)) and (
                            math.isnan(item) or math.isinf(item)
                        ):
                            self.logger.warning(
                                f"Invalid metric value in {key}: {item}"
                            )
                            return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating metrics: {e}")
            return False
