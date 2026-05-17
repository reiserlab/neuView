"""
Enhanced threshold service for handling all threshold computations and configurations.

This module provides a comprehensive threshold service that consolidates all
threshold-related logic, integrates with the threshold configuration system,
and provides advanced threshold calculation algorithms.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import hashlib

from .threshold_config import get_threshold_config, ThresholdConfig, ThresholdMethod

logger = logging.getLogger(__name__)


class ThresholdService:
    """
    Comprehensive threshold service for all threshold computations.

    This service provides methods for computing thresholds at different
    aggregation levels for synapse counts and neuron counts, with support
    for multiple calculation methods and configuration-driven behavior.
    """

    def __init__(self, config: Optional[ThresholdConfig] = None):
        """
        Initialize the threshold service.

        Args:
            config: Optional threshold configuration. If None, uses global config.
        """
        self.config = config or get_threshold_config()
        self._cache: Dict[str, Tuple[List[float], str]] = {}
        self._cache_enabled = True

    def enable_cache(self, enabled: bool = True) -> None:
        """Enable or disable threshold caching."""
        self._cache_enabled = enabled
        if not enabled:
            self._cache.clear()

    def clear_cache(self) -> None:
        """Clear the threshold computation cache."""
        self._cache.clear()

    def compute_thresholds(
        self,
        df: pd.DataFrame,
        n_bins: int = 5,
        method: str = "linear",
        profile_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute threshold lists for synapse and neuron counts at different aggregation levels.

        Parameters
        ----------
        df : pandas.DataFrame
            Input DataFrame with at least the following columns:
            - `"hex1"`, `"hex2"`: Column identifiers
            - `"layer"`: Layer index
            - `"region"`: Region name (e.g., `"ME"`, `"LO"`, `"LOP"`)
            - `"side"`: Side indicator (e.g., `"L"` or `"R"`)
            - `"total_synapses"`: Number of synapses
            - `"bodyId"`: Body identifier for neuron counting
        n_bins : int, optional
            Number of bins to divide the value ranges into. The returned threshold
            lists will each have `n_bins + 1` elements. Default is 5.
        method : str, optional
            Threshold calculation method. Default is 'linear'.
        profile_name : str, optional
            Name of threshold profile to use for configuration.

        Returns
        -------
        thresholds : dict
            A nested dictionary with the first level keyed by the metric
            ("total_synapses", "neuron_count"), then by scope ("all" or "layers"),
            and within "layers" by region ("ME", "LO", "LOP").
        """
        # Get configuration
        if profile_name:
            settings = self.config.get_settings(profile_name)
            if settings and settings.profile.method != ThresholdMethod.LINEAR:
                method = settings.profile.method.value
                n_bins = settings.profile.n_bins

        thresholds = {
            "total_synapses": {"all": None, "layers": {}},
            "neuron_count": {"all": None, "layers": {}},
        }

        # Guard clause for empty DataFrame
        if df.empty:
            logger.warning("Empty DataFrame provided to compute_thresholds")
            return thresholds

        # Check if required columns exist
        required_columns = [
            "hex1",
            "hex2",
            "side",
            "region",
            "total_synapses",
            "bodyId",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing required columns in DataFrame: {missing_columns}")
            return thresholds

        try:
            # Create cache key
            cache_key = self._create_cache_key(df, n_bins, method)

            # Check cache first
            if self._cache_enabled and cache_key in self._cache:
                cached_thresholds, timestamp = self._cache[cache_key]
                logger.debug(f"Using cached thresholds from {timestamp}")
                return self._deserialize_thresholds(cached_thresholds)

            # Across all layers - find the max per column across all regions.
            synapse_data = df.groupby(["hex1", "hex2", "side", "region"])[
                "total_synapses"
            ].sum()
            thresholds["total_synapses"]["all"] = self.calculate_thresholds(
                synapse_data, n_bins=n_bins, method=method
            )

            neuron_data = df.groupby(["hex1", "hex2", "side", "region"])[
                "bodyId"
            ].nunique()
            thresholds["neuron_count"]["all"] = self.calculate_thresholds(
                neuron_data, n_bins=n_bins, method=method
            )

            # Compute thresholds for each region
            for reg in ["ME", "LO", "LOP"]:
                sub = df[df["region"] == reg]

                if not sub.empty:
                    # Across layers - find the max per column/layer within regions
                    synapse_layer_data = sub.groupby(["hex1", "hex2", "side", "layer"])[
                        "total_synapses"
                    ].sum()
                    thresholds["total_synapses"]["layers"][reg] = (
                        self.calculate_thresholds(
                            synapse_layer_data, n_bins=n_bins, method=method
                        )
                    )
                    neuron_layer_data = sub.groupby(["hex1", "hex2", "side", "layer"])[
                        "bodyId"
                    ].nunique()
                    thresholds["neuron_count"]["layers"][reg] = (
                        self.calculate_thresholds(
                            neuron_layer_data, n_bins=n_bins, method=method
                        )
                    )
                else:
                    # Empty region - provide default thresholds
                    thresholds["total_synapses"]["layers"][reg] = [0.0] * (n_bins + 1)
                    thresholds["neuron_count"]["layers"][reg] = [0.0] * (n_bins + 1)

            # Cache the results
            if self._cache_enabled:
                serialized_thresholds = self._serialize_thresholds(thresholds)
                self._cache[cache_key] = (
                    serialized_thresholds,
                    datetime.now().isoformat(),
                )

            # Update configuration if profile was specified
            if profile_name:
                self._update_profile_thresholds(profile_name, thresholds)

        except Exception as e:
            logger.error(f"Error computing thresholds: {e}")
            # Return empty thresholds on error
            return {
                "total_synapses": {"all": None, "layers": {}},
                "neuron_count": {"all": None, "layers": {}},
            }

        return thresholds

    def calculate_thresholds(
        self, values: Any, n_bins: int = 5, method: str = "linear"
    ) -> List[float]:
        """
        Calculate thresholds using various methods.

        Args:
            values: Pandas Series, DataFrame, or other data structure containing numeric values
            n_bins: Number of bins to create (result will have n_bins + 1 thresholds)
            method: Calculation method ('linear', 'percentile', 'quantile', 'log_scale',
                   'standard_deviation', 'data_driven', 'adaptive')

        Returns:
            List of threshold values
        """
        # Handle both Series and DataFrame
        if hasattr(values, "empty") and values.empty:
            return [0.0] * (n_bins + 1)

        try:
            # Convert to Series if it's a DataFrame
            if isinstance(values, pd.DataFrame):
                values = values.iloc[:, 0] if len(values.columns) > 0 else pd.Series()

            if hasattr(values, "empty") and values.empty:
                return [0.0] * (n_bins + 1)

            # Convert to numpy array for calculations
            values_array = (
                np.array(values.dropna())
                if hasattr(values, "dropna")
                else np.array(values)
            )

            if len(values_array) == 0:
                return [0.0] * (n_bins + 1)

            # Apply the specified method
            if method == "linear":
                return self._linear_thresholds(values_array, n_bins)
            elif method == "percentile":
                return self._percentile_thresholds(values_array, n_bins)
            elif method == "quantile":
                return self._quantile_thresholds(values_array, n_bins)
            elif method == "log_scale":
                return self._log_scale_thresholds(values_array, n_bins)
            elif method == "standard_deviation":
                return self._std_dev_thresholds(values_array, n_bins)
            elif method == "data_driven":
                return self._data_driven_thresholds(values_array, n_bins)
            elif method == "adaptive":
                return self._adaptive_thresholds(values_array, n_bins)
            else:
                logger.warning(f"Unknown threshold method: {method}, using linear")
                return self._linear_thresholds(values_array, n_bins)

        except (TypeError, ValueError) as e:
            logger.warning(f"Error calculating thresholds: {e}")
            return [0.0] * (n_bins + 1)

    def _linear_thresholds(self, values: np.ndarray, n_bins: int) -> List[float]:
        """Calculate linear thresholds between min and max."""
        vmin = float(values.min())
        vmax = float(values.max())

        if vmax == vmin:
            return [vmin] * (n_bins + 1)

        return [vmin + (vmax - vmin) * (i / n_bins) for i in range(n_bins + 1)]

    def _percentile_thresholds(self, values: np.ndarray, n_bins: int) -> List[float]:
        """Calculate thresholds based on percentiles."""
        percentiles = np.linspace(0, 100, n_bins + 1)
        return [float(np.percentile(values, p)) for p in percentiles]

    def _quantile_thresholds(self, values: np.ndarray, n_bins: int) -> List[float]:
        """Calculate thresholds based on quantiles."""
        quantiles = np.linspace(0, 1, n_bins + 1)
        return [float(np.quantile(values, q)) for q in quantiles]

    def _log_scale_thresholds(self, values: np.ndarray, n_bins: int) -> List[float]:
        """Calculate log-scale thresholds for highly skewed data."""
        positive_values = values[values > 0]
        if len(positive_values) == 0:
            return [0.0] * (n_bins + 1)

        log_values = np.log10(positive_values)
        log_min, log_max = log_values.min(), log_values.max()

        if log_min == log_max:
            return [float(positive_values[0])] * (n_bins + 1)

        log_thresholds = np.linspace(log_min, log_max, n_bins + 1)
        return [float(10**log_t) for log_t in log_thresholds]

    def _std_dev_thresholds(self, values: np.ndarray, n_bins: int) -> List[float]:
        """Calculate thresholds based on standard deviation."""
        mean_val = values.mean()
        std_val = values.std()

        if std_val == 0:
            return [float(mean_val)] * (n_bins + 1)

        # Create thresholds at mean ± n*std_dev
        factors = np.linspace(-2, 2, n_bins + 1)
        thresholds = [float(mean_val + factor * std_val) for factor in factors]

        # Clamp to data range
        min_val, max_val = values.min(), values.max()
        thresholds = [max(min_val, min(max_val, t)) for t in thresholds]

        return sorted(thresholds)

    def _data_driven_thresholds(self, values: np.ndarray, n_bins: int) -> List[float]:
        """Calculate data-driven thresholds based on distribution characteristics."""
        q25, q50, q75 = np.percentile(values, [25, 50, 75])
        min_val, max_val = values.min(), values.max()

        # Start with quartiles
        thresholds = [
            float(min_val),
            float(q25),
            float(q50),
            float(q75),
            float(max_val),
        ]

        # Add additional thresholds if needed
        while len(thresholds) < n_bins + 1:
            # Find the largest gap and split it
            gaps = [
                (thresholds[i + 1] - thresholds[i], i)
                for i in range(len(thresholds) - 1)
            ]
            largest_gap, idx = max(gaps)

            if largest_gap > 0:
                new_threshold = (thresholds[idx] + thresholds[idx + 1]) / 2
                thresholds.insert(idx + 1, new_threshold)
            else:
                break

        # Trim to exact number needed
        if len(thresholds) > n_bins + 1:
            # Keep most representative thresholds
            indices = np.linspace(0, len(thresholds) - 1, n_bins + 1, dtype=int)
            thresholds = [thresholds[i] for i in indices]

        return sorted(thresholds)

    def _adaptive_thresholds(self, values: np.ndarray, n_bins: int) -> List[float]:
        """Calculate adaptive thresholds based on data distribution."""
        # Analyze data distribution
        skewness = self._calculate_skewness(values)
        variance = values.var()

        if abs(skewness) > 1.0:
            # Highly skewed data - use log scale if possible
            if np.all(values > 0):
                return self._log_scale_thresholds(values, n_bins)
            else:
                return self._percentile_thresholds(values, n_bins)
        elif variance / values.mean() > 2.0:
            # High variance - use data-driven approach
            return self._data_driven_thresholds(values, n_bins)
        else:
            # Normal distribution - use linear thresholds
            return self._linear_thresholds(values, n_bins)

    def _calculate_skewness(self, values: np.ndarray) -> float:
        """Calculate skewness of the data."""
        from scipy.stats import skew

        return float(skew(values))

    def layer_thresholds(self, values: Any, n_bins: int = 5) -> List[float]:
        """
        Backward compatibility method for layer thresholds.

        This method maintains the original interface while using the enhanced
        calculation methods.
        """
        return self.calculate_thresholds(values, n_bins, method="linear")



    def validate_thresholds(self, thresholds: List[float]) -> bool:
        """
        Validate that thresholds are properly ordered and contain valid values.

        Args:
            thresholds: List of threshold values to validate

        Returns:
            True if thresholds are valid, False otherwise
        """
        if not thresholds:
            return False

        try:
            # Check that all values are numeric
            numeric_thresholds = [float(t) for t in thresholds]

            # Check that thresholds are in ascending order
            for i in range(1, len(numeric_thresholds)):
                if numeric_thresholds[i] < numeric_thresholds[i - 1]:
                    return False

            return True

        except (TypeError, ValueError):
            return False



    def get_roi_filtering_threshold(
        self, profile_name: str = "roi_filtering_default"
    ) -> float:
        """
        Get the ROI filtering threshold from configuration.

        Args:
            profile_name: Name of the ROI filtering threshold profile

        Returns:
            The configured threshold value
        """
        return self.config.get_threshold_value(profile_name)

    def get_performance_thresholds(self) -> Dict[str, float]:
        """
        Get performance monitoring thresholds.

        Returns:
            Dictionary containing performance threshold values
        """
        return {
            "slow_operation": self.config.get_threshold_value(
                "performance_slow_operation"
            ),
            "very_slow_operation": self.config.get_threshold_value(
                "performance_very_slow_operation"
            ),
        }

    def get_memory_thresholds(self) -> Dict[str, float]:
        """
        Get memory optimization thresholds.

        Returns:
            Dictionary containing memory threshold values
        """
        return {
            "optimization_trigger": self.config.get_threshold_value(
                "memory_optimization_trigger"
            ),
            "warning_level": self.config.get_threshold_value("memory_warning_level"),
        }

    def _create_cache_key(self, df: pd.DataFrame, n_bins: int, method: str) -> str:
        """Create a cache key for threshold computation."""
        # Create a hash based on dataframe shape, columns, and parameters
        df_signature = f"{df.shape}_{sorted(df.columns)}_{df.dtypes.to_dict()}"
        params_signature = f"{n_bins}_{method}"
        combined = f"{df_signature}_{params_signature}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _serialize_thresholds(self, thresholds: Dict[str, Any]) -> List[float]:
        """Serialize threshold dictionary to a flat list for caching."""
        flat_list = []
        if thresholds.get("total_synapses", {}).get("all"):
            flat_list.extend(thresholds["total_synapses"]["all"])
        if thresholds.get("neuron_count", {}).get("all"):
            flat_list.extend(thresholds["neuron_count"]["all"])
        # Add layer thresholds
        for region in ["ME", "LO", "LOP"]:
            if thresholds.get("total_synapses", {}).get("layers", {}).get(region):
                flat_list.extend(thresholds["total_synapses"]["layers"][region])
            if thresholds.get("neuron_count", {}).get("layers", {}).get(region):
                flat_list.extend(thresholds["neuron_count"]["layers"][region])
        return flat_list

    def _deserialize_thresholds(self, flat_list: List[float]) -> Dict[str, Any]:
        """Deserialize flat list back to threshold dictionary structure."""
        # This is a simplified version - in practice, you'd need to store
        # metadata about the structure to properly reconstruct
        thresholds = {
            "total_synapses": {"all": None, "layers": {}},
            "neuron_count": {"all": None, "layers": {}},
        }
        # For now, return empty structure - implement proper deserialization
        # based on your specific needs
        return thresholds

    def _update_profile_thresholds(
        self, profile_name: str, thresholds: Dict[str, Any]
    ) -> None:
        """Update threshold configuration with computed thresholds."""
        try:
            # Extract representative thresholds for the profile
            if thresholds.get("total_synapses", {}).get("all"):
                computed_thresholds = thresholds["total_synapses"]["all"]
                self.config.update_computed_thresholds(
                    profile_name,
                    computed_thresholds,
                    cache_key=self._create_cache_key(pd.DataFrame(), 5, "linear"),
                )
        except Exception as e:
            logger.warning(f"Failed to update profile thresholds: {e}")
