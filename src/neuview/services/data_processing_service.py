"""
Data Processing Service

Handles data aggregation, processing, and transformation operations for neuron analysis,
extracting logic from PageGenerator to improve modularity and testability.
"""

import logging
import pandas as pd
import numpy as np
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class DataProcessingService:
    """Service for data processing and aggregation operations."""

    def __init__(self, page_generator):
        """Initialize data processing service.

        Args:
            page_generator: Page generator instance for accessing utilities and config
        """
        self.page_generator = page_generator
        self.config = page_generator.config

    def aggregate_roi_data(
        self,
        roi_counts_df: pd.DataFrame,
        neurons_df: pd.DataFrame,
        soma_side: str,
        connector=None,
    ) -> List[Dict[str, Any]]:
        """Aggregate ROI data across neurons matching the specific soma side.

        Gets total pre/post synapses per ROI (primary ROIs only).

        Args:
            roi_counts_df: DataFrame with ROI count data
            neurons_df: DataFrame with neuron data
            soma_side: Soma side filter
            connector: Optional NeuPrint connector for getting primary ROIs

        Returns:
            List of dictionaries with aggregated ROI data
        """
        if (
            roi_counts_df is None
            or roi_counts_df.empty
            or neurons_df is None
            or neurons_df.empty
        ):
            return []

        # Filter ROI data to include only neurons that belong to this specific soma side
        if "bodyId" in neurons_df.columns and "bodyId" in roi_counts_df.columns:
            # Get bodyIds of neurons that match this soma side
            soma_side_body_ids = set(neurons_df["bodyId"].values)
            # Filter ROI counts to include only these neurons
            roi_counts_soma_filtered = roi_counts_df[
                roi_counts_df["bodyId"].isin(list(soma_side_body_ids))
            ]
        else:
            # If bodyId columns are not available, fall back to using all ROI data
            # This shouldn't happen in normal operation but provides a safety net
            roi_counts_soma_filtered = roi_counts_df

        if roi_counts_soma_filtered.empty:
            return []

        # Get dataset-aware primary ROIs
        primary_rois = self.page_generator._get_primary_rois(connector)

        # Convert primary_rois to list if it's a numpy array
        if hasattr(primary_rois, "tolist"):
            primary_rois = primary_rois.tolist()
        elif not isinstance(primary_rois, list):
            primary_rois = list(primary_rois) if primary_rois is not None else []

        # Filter ROI counts to include only primary ROIs
        if len(primary_rois) > 0:
            roi_counts_filtered = roi_counts_soma_filtered[
                roi_counts_soma_filtered["roi"].isin(primary_rois)
            ]
        else:
            # If no primary ROIs available, return empty
            return []

        if roi_counts_filtered.empty:
            return []

        # Group by ROI and sum pre/post synapses across all neurons
        roi_aggregated = (
            roi_counts_filtered.groupby("roi")
            .agg({"pre": "sum", "post": "sum", "downstream": "sum", "upstream": "sum"})
            .reset_index()
        )

        # Calculate total synapses per ROI
        roi_aggregated["total"] = roi_aggregated["pre"] + roi_aggregated["post"]

        # Calculate total pre-synapses across all ROIs for percentage calculation
        total_pre_synapses = roi_aggregated["pre"].sum()

        # Calculate percentage of pre-synapses for each ROI
        if total_pre_synapses > 0:
            roi_aggregated["pre_percentage"] = (
                roi_aggregated["pre"] / total_pre_synapses * 100
            )
        else:
            roi_aggregated["pre_percentage"] = 0.0

        total_post_synapses = roi_aggregated["post"].sum()

        # Calculate percentage of post-synapses for each ROI
        if total_post_synapses > 0:
            roi_aggregated["post_percentage"] = (
                roi_aggregated["post"] / total_post_synapses * 100
            )
        else:
            roi_aggregated["post_percentage"] = 0.0

        # Sort by total synapses (descending) to show most innervated ROIs first
        roi_aggregated = roi_aggregated.sort_values("total", ascending=False)

        # Convert to list of dictionaries for template
        roi_summary = []
        for _, row in roi_aggregated.iterrows():
            post_val = int(row["post"])
            pre_val = int(row["pre"])

            roi_entry = {
                "name": row["roi"],
                "pre": pre_val,
                "post": post_val,
                "total": int(row["total"]),
                "pre_percentage": float(row["pre_percentage"]),
                "post_percentage": float(row["post_percentage"]),
                "downstream": int(row["downstream"]),
                "upstream": int(row["upstream"]),
            }
            roi_summary.append(roi_entry)

        return roi_summary

    def get_column_layer_values(
        self, neuron_type: str, connector
    ) -> Tuple[pd.DataFrame, Dict, Dict]:
        """Query dataset to get synapse density and neuron count per column across layer ROIs.

        Args:
            neuron_type: Type of neuron being analyzed
            connector: NeuPrint connector instance for database queries

        Returns:
            Tuple of (results_df, thresholds, min_max_data)
        """
        # Setup cache
        cache_dir = Path("output/.cache/col_layers")
        cache_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", neuron_type).strip("_")
        cache_path = cache_dir / f"{safe_name}.json"

        # Try to load from cache
        cached_result = self._load_column_layer_cache(cache_path)
        if cached_result is not None:
            return cached_result

        # Query data from database
        layer_pattern = r"^(ME|LO|LOP)_([LR])_layer_(\d+)$"
        query = self._build_column_layer_query(neuron_type)

        try:
            df = connector.client.fetch_custom(query)
            df = self._clean_column_layer_data(df)

            # Compute thresholds for colorscales using ThresholdService
            threshold_service = self.page_generator.threshold_service
            thresholds = threshold_service.compute_thresholds(df, n_bins=5)

            # Process and aggregate data
            results, min_max_data = self._process_column_layer_data(
                df, layer_pattern, connector
            )

            # Save to cache
            self._save_column_layer_cache(cache_path, results, thresholds, min_max_data)

            return results, thresholds, min_max_data

        except Exception as e:
            logger.warning(f"Error querying column layer data for {neuron_type}: {e}")
            return pd.DataFrame(), {}, {}

    def _load_column_layer_cache(
        self, cache_path: Path
    ) -> Optional[Tuple[pd.DataFrame, Dict, Dict]]:
        """Load column layer data from cache if available."""
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            if (
                isinstance(cached, dict)
                and "results" in cached
                and "thresholds" in cached
            ):
                results_df = pd.DataFrame(cached["results"])
                min_max_data = cached.get("min_max_data", {})
                return results_df, cached["thresholds"], min_max_data
        except Exception as e:
            logger.debug(f"Failed to load cache from {cache_path}: {e}")

        return None

    def _build_column_layer_query(self, neuron_type: str) -> str:
        """Build the NeuPrint query for column layer data."""
        return f"""
        MATCH (n:Neuron)-[:Contains]->(nss:SynapseSet)-[:Contains]->(ns:Synapse)
        WHERE n.type = "{neuron_type}"
        WITH DISTINCT ns
        WITH ns,  CASE
               WHEN exists(ns['ME(R)']) THEN ['ME', 'R']
               WHEN exists(ns['ME(L)']) THEN ['ME', 'L']
               WHEN exists(ns['LO(R)']) THEN ['LO', 'R']
               WHEN exists(ns['LO(L)']) THEN ['LO', 'L']
               WHEN exists(ns['LOP(R)']) THEN ['LOP', 'R']
               WHEN exists(ns['LOP(L)']) THEN ['LOP', 'L']
             END AS layerKey,
             count(ns) AS n_synapses
        RETURN
            ns.olHex1 AS hex1,
            ns.olHex2 AS hex2,
            ns.olLayer AS layer,
            layerKey[0] as region,
            layerKey[1] as side,
            sum(n_synapses) as total_synapses,
            ns.bodyId as bodyId,
            count(DISTINCT ns.bodyId) as neuron_count
        ORDER BY hex1, hex2, layer
        """

    def _clean_column_layer_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate column layer data."""
        # Create explicit copy to avoid SettingWithCopyWarning
        df = df.dropna(subset=["layer"]).copy()
        df["layer"] = df["layer"].astype(int)
        df["hex1"] = df["hex1"].astype(int)
        df["hex2"] = df["hex2"].astype(int)
        return df

    def _process_column_layer_data(
        self, df: pd.DataFrame, layer_pattern: str, connector
    ) -> Tuple[pd.DataFrame, Dict]:
        """Process column layer data into final format."""
        # Aggregate data
        df_unique = df.groupby(
            ["hex1", "hex2", "layer", "side", "region"], as_index=False
        ).agg(
            total_synapses=("total_synapses", "sum"),
            neuron_count=("bodyId", pd.Series.nunique),
        )

        # Get all possible layers per region/side
        all_layers = self.page_generator._get_all_dataset_layers(
            layer_pattern, connector
        )
        layer_map = {}
        for region, side, layer in all_layers:
            layer_map.setdefault((region, side), []).append(layer)

        # Calculate min/max for normalization
        max_syn_region = df_unique.groupby(["region"])["total_synapses"].max()
        max_cells_region = df_unique.groupby(["region"])["neuron_count"].max()
        min_syn_region = df_unique.groupby(["region"])["total_synapses"].min()
        min_cells_region = df_unique.groupby(["region"])["neuron_count"].min()

        min_max_data = {
            "min_syn_region": min_syn_region.to_dict(),
            "max_syn_region": max_syn_region.to_dict(),
            "min_cells_region": min_cells_region.to_dict(),
            "max_cells_region": max_cells_region.to_dict(),
        }

        # Build results
        results = []
        for group_key, group in df_unique.groupby(["hex1", "hex2", "region", "side"]):
            hex1, hex2, region, side = list(group_key)
            layers_for_group = sorted(layer_map[(region, side)])
            max_layer = max(layers_for_group)

            # Initialize lists with zeros
            synapse_list = [0] * max_layer
            neuron_list = [0] * max_layer

            # Fill values where data exists
            for _, row in group.iterrows():
                idx = int(row["layer"]) - 1
                synapse_list[idx] = int(row["total_synapses"])
                neuron_list[idx] = int(row["neuron_count"])

            results.append(
                {
                    "hex1": int(hex1),
                    "hex2": int(hex2),
                    "region": region,
                    "side": side,
                    "synapses_list": synapse_list,  # Backward compatible column name
                    "neurons_list": neuron_list,  # Backward compatible column name
                    "layers": [
                        {
                            "layer_index": i + 1,
                            "synapse_count": int(synapse_list[i])
                            if i < len(synapse_list)
                            else 0,
                            "neuron_count": int(neuron_list[i])
                            if i < len(neuron_list)
                            else 0,
                            "value": float(synapse_list[i])
                            if i < len(synapse_list)
                            else 0.0,
                        }
                        for i in range(max(len(synapse_list), len(neuron_list)))
                    ],
                }
            )

        return pd.DataFrame(results), min_max_data

    def _save_column_layer_cache(
        self,
        cache_path: Path,
        results: pd.DataFrame,
        thresholds: Dict,
        min_max_data: Dict,
    ):
        """Save column layer data to cache."""
        try:
            # Convert to JSON-serializable format
            results_dict = results.to_dict("records")

            # Ensure all values are JSON-serializable
            for record in results_dict:
                for key, value in record.items():
                    if key in ["hex1", "hex2"]:
                        record[key] = int(value)
                    elif isinstance(value, (np.integer, np.floating)):
                        record[key] = value.item()
                    elif isinstance(value, np.ndarray):
                        record[key] = value.tolist()
                    elif isinstance(value, list):
                        record[key] = [
                            v.item() if isinstance(v, (np.integer, np.floating)) else v
                            for v in value
                        ]

            # Make thresholds JSON-serializable
            json_thresholds = {}
            for key, value in thresholds.items():
                if isinstance(value, (np.integer, np.floating)):
                    json_thresholds[key] = value.item()
                elif isinstance(value, np.ndarray):
                    json_thresholds[key] = value.tolist()
                elif isinstance(value, list):
                    json_thresholds[key] = [
                        v.item() if isinstance(v, (np.integer, np.floating)) else v
                        for v in value
                    ]
                else:
                    json_thresholds[key] = value

            cache_data = {
                "results": results_dict,
                "thresholds": json_thresholds,
                "min_max_data": min_max_data,
            }

            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save cache to {cache_path}: {e}")

    def normalize_data_for_visualization(
        self, data: List[Dict], normalization_method: str = "minmax"
    ) -> List[Dict]:
        """Normalize data for visualization purposes.

        Args:
            data: List of data dictionaries
            normalization_method: Method for normalization ('minmax', 'zscore', etc.)

        Returns:
            Normalized data
        """
        if not data:
            return data

        try:
            if normalization_method == "minmax":
                return self._minmax_normalize(data)
            elif normalization_method == "zscore":
                return self._zscore_normalize(data)
            else:
                logger.warning(f"Unknown normalization method: {normalization_method}")
                return data
        except Exception as e:
            logger.warning(f"Error normalizing data: {e}")
            return data

    def _minmax_normalize(self, data: List[Dict]) -> List[Dict]:
        """Apply min-max normalization to numerical fields."""
        # Implementation would go here based on specific requirements
        return data

    def _zscore_normalize(self, data: List[Dict]) -> List[Dict]:
        """Apply z-score normalization to numerical fields."""
        # Implementation would go here based on specific requirements
        return data

    def filter_data_by_threshold(
        self,
        data: List[Dict],
        threshold_field: str,
        threshold_value: float,
        operator: str = "gte",
    ) -> List[Dict]:
        """Filter data based on threshold criteria.

        Args:
            data: List of data dictionaries
            threshold_field: Field name to apply threshold to
            threshold_value: Threshold value
            operator: Comparison operator ('gte', 'lte', 'gt', 'lt', 'eq')

        Returns:
            Filtered data list
        """
        if not data:
            return data

        try:
            filtered_data = []
            for item in data:
                if threshold_field not in item:
                    continue

                value = item[threshold_field]
                if not isinstance(value, (int, float)):
                    continue

                if operator == "gte" and value >= threshold_value:
                    filtered_data.append(item)
                elif operator == "lte" and value <= threshold_value:
                    filtered_data.append(item)
                elif operator == "gt" and value > threshold_value:
                    filtered_data.append(item)
                elif operator == "lt" and value < threshold_value:
                    filtered_data.append(item)
                elif operator == "eq" and value == threshold_value:
                    filtered_data.append(item)

            return filtered_data

        except Exception as e:
            logger.warning(f"Error filtering data: {e}")
            return data
