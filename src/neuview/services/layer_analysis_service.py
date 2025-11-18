"""
Layer Analysis Service for neuView.

This service handles layer-based ROI analysis that was previously part of the
PageGenerator class. It analyzes ROI data for layer-based regions matching
patterns like (ME|LO|LOP)_[LR]_layer_<number> and provides comprehensive
layer analysis including central brain, AME, and LA regions.
"""

import logging
import re
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LayerAnalysisService:
    """Service for analyzing layer-based ROI data and generating layer summaries."""

    def __init__(self, config=None):
        """Initialize layer analysis service.

        Args:
            config: Optional configuration object for dataset information
        """
        self.config = config

    def analyze_layer_roi_data(
        self,
        roi_counts_df: pd.DataFrame,
        neurons_df: pd.DataFrame,
        soma_side: str,
        neuron_type: str,
        connector,
    ) -> Optional[Dict[str, Any]]:
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

        Returns:
            Dictionary containing layer analysis results or None if no layer data
        """
        if (
            roi_counts_df is None
            or roi_counts_df.empty
            or neurons_df is None
            or neurons_df.empty
        ):
            return None

        # Filter ROI data to include only neurons that belong to this specific soma side
        roi_counts_soma_filtered = self._filter_roi_data_by_soma_side(
            roi_counts_df, neurons_df
        )

        if roi_counts_soma_filtered.empty:
            return None

        # Pattern to match layer ROIs: (ME|LO|LOP)_[LR]_layer_<number>
        layer_pattern = r"^(ME|LO|LOP)_([LR])_layer_(\d+)$"

        # Filter ROIs that match the layer pattern
        layer_rois = roi_counts_soma_filtered[
            roi_counts_soma_filtered["roi"].str.match(layer_pattern, na=False)
        ].copy()

        # Filter ROI data to include only ROIs in the ipsilateral optic lobe.
        layer_rois_filtered = self._filter_roi_data_by_optic_lobe_side(
            layer_rois, soma_side
        )

        # Check if we have any layer connections (ME, LO, or LOP layers)
        has_layer_connections = not layer_rois_filtered.empty

        if not has_layer_connections:
            return None

        # Since we have layer connections, always show the table with required entries
        additional_roi_data = self._analyze_additional_rois(
            roi_counts_soma_filtered, connector
        )

        # Extract layer information and aggregate by layer
        layer_info = self._extract_layer_information(layer_rois_filtered, layer_pattern)

        if not layer_info:
            return None

        # Query the ENTIRE dataset for all available layers (not just this neuron type)
        all_dataset_layers = self._get_all_dataset_layers(layer_pattern, connector)

        # Process layer data and calculate aggregations
        layer_aggregated = self._aggregate_layer_data(layer_info)

        # Create complete layer summary including all dataset layers
        layer_summary = self._create_layer_summary(
            additional_roi_data,
            layer_aggregated,
            all_dataset_layers,
            soma_side,
            layer_info,
        )

        # Organize data into containers for visualization
        containers = self._organize_data_into_containers(
            layer_summary, layer_info, all_dataset_layers
        )

        # Calculate percentages across containers
        self._calculate_container_percentages(containers)

        # Generate summary statistics
        summary_stats = self._generate_summary_statistics(layer_summary)

        return {
            "containers": containers,
            "layers": layer_summary,
            "summary": summary_stats,
        }

    def _filter_roi_data_by_soma_side(
        self, roi_counts_df: pd.DataFrame, neurons_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Filter ROI data to include only neurons from specific soma side."""
        if "bodyId" in neurons_df.columns and "bodyId" in roi_counts_df.columns:
            soma_side_body_ids = list(neurons_df["bodyId"].values)
            return roi_counts_df[roi_counts_df["bodyId"].isin(soma_side_body_ids)]
        else:
            return roi_counts_df

    def _filter_roi_data_by_optic_lobe_side(
        self, layer_rois: pd.DataFrame, soma_side: str
    ) -> pd.DataFrame:
        """Filter ROI data to include only ROIs from the ipsilateral optic lobe
        side to the soma side. Use the ipsilateral side to ensure that the layer
         table data matches the hexagonal eyemap plots."""
        if soma_side == "combined":
            layer_rois_filtered = layer_rois
        else:
            side_key = {"left": "_L_", "right": "_R_"}
            if soma_side not in side_key:
                raise ValueError(
                    f"Unsupported soma_side: {soma_side!r} (use 'left', 'right', or 'combined')"
                )
            pattern = side_key[soma_side]
            mask = (
                layer_rois["roi"]
                .astype("string")
                .str.contains(pattern, regex=False, na=False)
            )
            layer_rois_filtered = layer_rois.loc[mask]
        return layer_rois_filtered

    def _analyze_additional_rois(
        self, roi_counts_soma_filtered: pd.DataFrame, connector
    ) -> List[Dict[str, Any]]:
        """Analyze central brain, AME, and LA ROIs."""
        additional_roi_data = []
        all_rois = roi_counts_soma_filtered["roi"].unique().tolist()

        # Get dataset-specific central brain ROIs
        from ..dataset_adapters import DatasetAdapterFactory

        # Get the appropriate adapter for this dataset
        dataset_name = "optic-lobe"  # default
        if self.config:
            try:
                dataset_name = self.config.neuprint.dataset
            except AttributeError:
                pass  # Use default if config structure is incomplete

        adapter = DatasetAdapterFactory.create_adapter(dataset_name)
        central_brain_rois = adapter.query_central_brain_rois(all_rois)

        # Add central brain entry
        central_brain_data = self._calculate_roi_data(
            roi_counts_soma_filtered, central_brain_rois, "central brain"
        )
        additional_roi_data.append(central_brain_data)

        # Add AME entry
        ame_data = self._calculate_single_roi_data(
            roi_counts_soma_filtered, all_rois, "AME"
        )
        additional_roi_data.append(ame_data)

        # Add LA entry
        la_data = self._calculate_single_roi_data(
            roi_counts_soma_filtered, all_rois, "LA"
        )
        additional_roi_data.append(la_data)

        return additional_roi_data

    def _calculate_roi_data(
        self,
        roi_counts_soma_filtered: pd.DataFrame,
        target_rois: List[str],
        roi_name: str,
    ) -> Dict[str, Any]:
        """Calculate aggregated data for a set of ROIs."""
        pre_total = 0
        post_total = 0
        bodyids = set()

        for roi in target_rois:
            matching_rois = roi_counts_soma_filtered[
                roi_counts_soma_filtered["roi"] == roi
            ]
            if not matching_rois.empty:
                pre_total += matching_rois["pre"].fillna(0).sum()
                post_total += matching_rois["post"].fillna(0).sum()
                bodyids.update(matching_rois["bodyId"].unique())

        neuron_count = len(bodyids)

        # Calculate mean synapses per neuron using dash vs 0.0 logic
        mean_pre = self._calculate_mean_or_dash(pre_total, neuron_count)
        mean_post = self._calculate_mean_or_dash(post_total, neuron_count)

        if mean_pre == "-" and mean_post == "-":
            mean_total = "-"
        elif mean_pre == "-":
            mean_total = mean_post
        elif mean_post == "-":
            mean_total = mean_pre
        else:
            mean_total = mean_pre + mean_post

        return {
            "roi": roi_name,
            "region": roi_name,
            "side": "Combined",
            "layer": 0,  # Not a layer, but we use 0 to distinguish
            "bodyId": neuron_count,
            "pre": mean_pre,
            "post": mean_post,
            "total": mean_total,
        }

    def _calculate_single_roi_data(
        self, roi_counts_soma_filtered: pd.DataFrame, all_rois: List[str], roi_base: str
    ) -> Dict[str, Any]:
        """Calculate data for a single ROI (like AME or LA)."""
        pre_total = 0
        post_total = 0
        bodyids = set()

        for roi in all_rois:
            roi_cleaned = (
                roi.replace("(L)", "")
                .replace("(R)", "")
                .replace("_L", "")
                .replace("_R", "")
            )
            if roi_cleaned == roi_base:
                matching_rois = roi_counts_soma_filtered[
                    roi_counts_soma_filtered["roi"] == roi
                ]
                if not matching_rois.empty:
                    pre_total += matching_rois["pre"].fillna(0).sum()
                    post_total += matching_rois["post"].fillna(0).sum()
                    bodyids.update(matching_rois["bodyId"].unique())

        neuron_count = len(bodyids)

        # Calculate mean synapses per neuron using dash vs 0.0 logic
        mean_pre = self._calculate_mean_or_dash(pre_total, neuron_count)
        mean_post = self._calculate_mean_or_dash(post_total, neuron_count)

        if mean_pre == "-" and mean_post == "-":
            mean_total = "-"
        elif mean_pre == "-":
            mean_total = mean_post
        elif mean_post == "-":
            mean_total = mean_pre
        else:
            mean_total = mean_pre + mean_post

        return {
            "roi": roi_base,
            "region": roi_base,
            "side": "Combined",
            "layer": 0,
            "bodyId": neuron_count,
            "pre": mean_pre,
            "post": mean_post,
            "total": mean_total,
        }

    def _calculate_mean_or_dash(self, total_synapses: float, neuron_count: int):
        """Calculate mean synapses per neuron with special handling for no synapses."""
        if neuron_count == 0 or total_synapses == 0:
            return "-"  # No synapses at all
        mean = total_synapses / neuron_count
        return mean if mean > 0 else 0.0  # Show 0.0 if rounds to zero but has synapses

    def _extract_layer_information(
        self, layer_rois: pd.DataFrame, layer_pattern: str
    ) -> List[Dict[str, Any]]:
        """Extract layer information from layer ROIs."""
        layer_info = []
        for _, row in layer_rois.iterrows():
            roi_name = str(row["roi"])
            match = re.match(layer_pattern, roi_name)
            if match:
                region, side, layer_num = match.groups()
                pre_val = row.get("pre", 0) if "pre" in row else 0
                post_val = row.get("post", 0) if "post" in row else 0
                total_val = row.get("total") if "total" in row else (pre_val + post_val)
                layer_info.append(
                    {
                        "roi": roi_name,
                        "region": region,
                        "side": side,
                        "layer": int(layer_num),
                        "bodyId": row["bodyId"],  # Include bodyId for proper grouping
                        "pre": pre_val,
                        "post": post_val,
                        "total": total_val,
                    }
                )
        return layer_info

    def _get_all_dataset_layers(
        self, layer_pattern: str, connector
    ) -> List[Tuple[str, str, int]]:
        """Query the entire dataset for all available layer patterns."""
        try:
            # Try to get ROI hierarchy for all available ROIs
            roi_hierarchy = connector._get_roi_hierarchy()
            if roi_hierarchy:

                def extract_roi_names(hierarchy_dict):
                    """Recursively extract ROI names from hierarchy."""
                    roi_names = []
                    if isinstance(hierarchy_dict, dict):
                        for key, value in hierarchy_dict.items():
                            # Remove * marker if present
                            clean_key = key.rstrip("*")
                            roi_names.append(clean_key)
                            if isinstance(value, dict):
                                roi_names.extend(extract_roi_names(value))
                    return roi_names

                all_rois = extract_roi_names(roi_hierarchy)
            else:
                # Fallback to empty list if hierarchy query fails
                all_rois = []
        except Exception as e:
            logger.warning(f"Failed to get ROI hierarchy for layer analysis: {e}")
            all_rois = []

        # Extract layer information from all ROIs
        all_layers = []
        for roi in all_rois:
            match = re.match(layer_pattern, roi)
            if match:
                region, side, layer_num = match.groups()
                all_layers.append((region, side, int(layer_num)))

        return sorted(set(all_layers))

    def _aggregate_layer_data(
        self, layer_info: List[Dict[str, Any]]
    ) -> Optional[pd.DataFrame]:
        """Aggregate layer data by region, side, and layer number."""
        if not layer_info:
            return None

        layer_df = pd.DataFrame(layer_info)

        # Group by region, side, and layer number to calculate mean synapses per neuron
        layer_aggregated = (
            layer_df.groupby(["region", "side", "layer"])
            .agg({"bodyId": "nunique", "pre": "sum", "post": "sum", "total": "sum"})
            .reset_index()
        )

        # Rename columns for clarity
        layer_aggregated = layer_aggregated.rename(
            columns={
                "bodyId": "neuron_count",
                "pre": "total_pre",
                "post": "total_post",
                "total": "total_synapses",
            }
        )

        # Calculate means for layer data
        layer_aggregated["mean_pre"] = layer_aggregated.apply(
            lambda row: self._calculate_mean_or_dash(
                row["total_pre"], row["neuron_count"]
            ),
            axis=1,
        )
        layer_aggregated["mean_post"] = layer_aggregated.apply(
            lambda row: self._calculate_mean_or_dash(
                row["total_post"], row["neuron_count"]
            ),
            axis=1,
        )
        layer_aggregated["mean_total"] = layer_aggregated.apply(
            lambda row: self._calculate_mean_or_dash(
                row["total_synapses"], row["neuron_count"]
            ),
            axis=1,
        )

        return layer_aggregated

    def _create_layer_summary(
        self,
        additional_roi_data: List[Dict[str, Any]],
        layer_aggregated: Optional[pd.DataFrame],
        all_dataset_layers: List[Tuple[str, str, int]],
        soma_side: str,
        layer_info: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Create complete layer summary including all dataset layers."""
        layer_summary = []

        # First add non-layer entries (central brain, AME, LA)
        for entry in additional_roi_data:
            layer_summary.append(
                {
                    "region": entry["region"],
                    "side": entry["side"],
                    "layer": entry["layer"],
                    "neuron_count": entry["bodyId"],
                    "pre": entry["pre"],
                    "post": entry["post"],
                    "total": entry["total"],
                    "total_pre": 0,  # These don't have separate total tracking
                    "total_post": 0,
                    "total_synapses": 0,
                }
            )

        # Get matching layer sides based on soma side
        matching_sides = self._get_matching_layer_sides(soma_side)
        added_layers = set()

        # Add all possible layer entries from dataset
        for region, side, layer_num in sorted(all_dataset_layers):
            if side not in matching_sides:
                continue

            layer_key = (region, side, layer_num)
            added_layers.add(layer_key)

            # Check if this layer has data in our aggregated results
            if layer_aggregated is not None:
                matching_rows = layer_aggregated[
                    (layer_aggregated["region"] == region)
                    & (layer_aggregated["side"] == side)
                    & (layer_aggregated["layer"] == layer_num)
                ]

                if not matching_rows.empty:
                    # Use actual data
                    row = matching_rows.iloc[0]
                    layer_summary.append(
                        {
                            "region": row["region"],
                            "side": row["side"],
                            "layer": int(row["layer"]),
                            "neuron_count": int(row["neuron_count"]),
                            "pre": (
                                row["mean_pre"]
                                if isinstance(row["mean_pre"], str)
                                else float(row["mean_pre"])
                            ),
                            "post": (
                                row["mean_post"]
                                if isinstance(row["mean_post"], str)
                                else float(row["mean_post"])
                            ),
                            "total": (
                                row["mean_total"]
                                if isinstance(row["mean_total"], str)
                                else float(row["mean_total"])
                            ),
                            "total_pre": int(row["total_pre"]),
                            "total_post": int(row["total_post"]),
                            "total_synapses": int(row["total_synapses"]),
                        }
                    )
                    continue

            # Add with 0 values if no data found
            layer_summary.append(
                {
                    "region": region,
                    "side": side,
                    "layer": layer_num,
                    "neuron_count": 0,
                    "pre": "-",
                    "post": "-",
                    "total": "-",
                    "total_pre": 0,
                    "total_post": 0,
                    "total_synapses": 0,
                }
            )

        # Also add any actual layer data that wasn't covered by dataset query
        if layer_aggregated is not None:
            layer_entries = layer_aggregated[layer_aggregated["layer"] > 0]
            for _, row in layer_entries.iterrows():
                layer_key = (row["region"], row["side"], int(row["layer"]))
                if layer_key not in added_layers:
                    layer_summary.append(
                        {
                            "region": row["region"],
                            "side": row["side"],
                            "layer": int(row["layer"]),
                            "neuron_count": int(row["neuron_count"]),
                            "pre": (
                                row["mean_pre"]
                                if isinstance(row["mean_pre"], str)
                                else float(row["mean_pre"])
                            ),
                            "post": (
                                row["mean_post"]
                                if isinstance(row["mean_post"], str)
                                else float(row["mean_post"])
                            ),
                            "total": (
                                row["mean_total"]
                                if isinstance(row["mean_total"], str)
                                else float(row["mean_total"])
                            ),
                            "total_pre": int(row["total_pre"]),
                            "total_post": int(row["total_post"]),
                            "total_synapses": int(row["total_synapses"]),
                        }
                    )

        return layer_summary

    def _get_matching_layer_sides(self, soma_side: str) -> List[str]:
        """Map soma_side values to layer side letters."""
        if soma_side == "left":
            return ["L"]
        elif soma_side == "right":
            return ["R"]
        elif soma_side in ["combined", "all"]:
            return ["L", "R"]
        else:
            # Default to all sides if soma_side is unclear
            return ["L", "R"]

    def _get_display_layer_name(self, region: str, layer_num: int) -> str:
        """Convert layer numbers to display names for specific regions."""
        if region == "LO":
            layer_mapping = {5: "5A", 6: "5B", 7: "6"}
            display_num = layer_mapping.get(layer_num, str(layer_num))
            return f"LO {display_num}"
        else:
            return f"{region} {layer_num}"

    def _organize_data_into_containers(
        self,
        layer_summary: List[Dict[str, Any]],
        layer_info: List[Dict[str, Any]],
        all_dataset_layers: List[Tuple[str, str, int]],
    ) -> Dict[str, Dict[str, Any]]:
        """Organize layer data into 6 containers for visualization."""
        containers = {
            "la": {"columns": ["LA"], "data": {}},
            "me": {"columns": [], "data": {}},
            "lo": {"columns": [], "data": {}},
            "lop": {"columns": [], "data": {}},
            "ame": {"columns": ["AME"], "data": {}},
            "central_brain": {"columns": ["central brain"], "data": {}},
        }

        # Collect all layers for each region type
        me_layers = set()
        lo_layers = set()
        lop_layers = set()

        # Get layers from dataset query
        for region, side, layer_num in all_dataset_layers:
            if region == "ME":
                me_layers.add(layer_num)
            elif region == "LO":
                lo_layers.add(layer_num)
            elif region == "LOP":
                lop_layers.add(layer_num)

        # Also collect layers from actual data
        for layer in layer_info:
            region = layer["region"]
            layer_num = layer["layer"]
            if region == "ME":
                me_layers.add(layer_num)
            elif region == "LO":
                lo_layers.add(layer_num)
            elif region == "LOP":
                lop_layers.add(layer_num)

        # Set up column headers for layer regions
        containers["me"]["columns"] = (
            [f"ME {i}" for i in sorted(me_layers)] + ["Total"] if me_layers else []
        )
        containers["lo"]["columns"] = (
            [self._get_display_layer_name("LO", i) for i in sorted(lo_layers)]
            + ["Total"]
            if lo_layers
            else []
        )
        containers["lop"]["columns"] = (
            [f"LOP {i}" for i in sorted(lop_layers)] + ["Total"] if lop_layers else []
        )

        # Initialize all container data with dashes (no synapses)
        for container_name, container in containers.items():
            container["data"] = {
                "pre": {col: "-" for col in container["columns"]},
                "post": {col: "-" for col in container["columns"]},
                "neuron_count": {col: 0 for col in container["columns"]},
            }
            container["percentage"] = {
                "pre": {col: 0.0 for col in container["columns"]},
                "post": {col: 0.0 for col in container["columns"]},
            }

        # Populate containers with actual mean data
        for layer in layer_summary:
            region = layer["region"]
            layer_num = layer["layer"]
            pre = layer["pre"]
            post = layer["post"]
            neuron_count = layer["neuron_count"]

            if region == "LA":
                containers["la"]["data"]["pre"]["LA"] = pre
                containers["la"]["data"]["post"]["LA"] = post
                containers["la"]["data"]["neuron_count"]["LA"] = neuron_count
            elif region == "AME":
                containers["ame"]["data"]["pre"]["AME"] = pre
                containers["ame"]["data"]["post"]["AME"] = post
                containers["ame"]["data"]["neuron_count"]["AME"] = neuron_count
            elif region == "central brain":
                containers["central_brain"]["data"]["pre"]["central brain"] = pre
                containers["central_brain"]["data"]["post"]["central brain"] = post
                containers["central_brain"]["data"]["neuron_count"]["central brain"] = (
                    neuron_count
                )
            elif region == "ME" and layer_num > 0:
                col_name = f"ME {layer_num}"
                if col_name in containers["me"]["data"]["pre"]:
                    containers["me"]["data"]["pre"][col_name] = pre
                    containers["me"]["data"]["post"][col_name] = post
                    containers["me"]["data"]["neuron_count"][col_name] = neuron_count
            elif region == "LO" and layer_num > 0:
                col_name = self._get_display_layer_name("LO", layer_num)
                if col_name in containers["lo"]["data"]["pre"]:
                    containers["lo"]["data"]["pre"][col_name] = pre
                    containers["lo"]["data"]["post"][col_name] = post
                    containers["lo"]["data"]["neuron_count"][col_name] = neuron_count
            elif region == "LOP" and layer_num > 0:
                col_name = f"LOP {layer_num}"
                if col_name in containers["lop"]["data"]["pre"]:
                    containers["lop"]["data"]["pre"][col_name] = pre
                    containers["lop"]["data"]["post"][col_name] = post
                    containers["lop"]["data"]["neuron_count"][col_name] = neuron_count

        # Calculate totals for multi-layer regions
        for region_name in ["me", "lo", "lop"]:
            container = containers[region_name]
            if "Total" in container["columns"]:
                self._calculate_container_totals(container)

        return containers

    def _calculate_container_totals(self, container: Dict[str, Any]):
        """Calculate totals for a container with multiple layers."""
        pre_sum = 0.0
        post_sum = 0.0
        total_neurons = 0
        layers_with_data = 0

        for col in container["columns"]:
            if col != "Total":
                pre_val = container["data"]["pre"][col]
                post_val = container["data"]["post"][col]
                neuron_count = container["data"]["neuron_count"][col]

                if isinstance(pre_val, (int, float)) and pre_val != "-":
                    pre_sum += pre_val
                    layers_with_data += 1
                if isinstance(post_val, (int, float)) and post_val != "-":
                    post_sum += post_val

                if neuron_count > 0:
                    total_neurons += neuron_count

        # Set totals as sum of layer means
        if layers_with_data > 0:
            container["data"]["pre"]["Total"] = pre_sum
            container["data"]["post"]["Total"] = post_sum
            container["data"]["neuron_count"]["Total"] = total_neurons
        else:
            container["data"]["pre"]["Total"] = "-"
            container["data"]["post"]["Total"] = "-"
            container["data"]["neuron_count"]["Total"] = 0

    def _calculate_container_percentages(self, containers: Dict[str, Dict[str, Any]]):
        """Calculate percentages for each container."""
        # First, calculate total synapses across all containers
        total_all_pre = 0
        total_all_post = 0

        for container_name, container in containers.items():
            for col in container["columns"]:
                pre_val = container["data"]["pre"][col]
                post_val = container["data"]["post"][col]

                if isinstance(pre_val, (int, float)) and pre_val != "-":
                    total_all_pre += pre_val
                if isinstance(post_val, (int, float)) and post_val != "-":
                    total_all_post += post_val

        # Calculate percentages for each container
        for container_name, container in containers.items():
            for col in container["columns"]:
                pre_val = container["data"]["pre"][col]
                post_val = container["data"]["post"][col]

                # Calculate pre percentage
                if (
                    isinstance(pre_val, (int, float))
                    and pre_val != "-"
                    and total_all_pre > 0
                ):
                    container["percentage"]["pre"][col] = (
                        pre_val / total_all_pre
                    ) * 100
                else:
                    container["percentage"]["pre"][col] = 0.0

                # Calculate post percentage
                if (
                    isinstance(post_val, (int, float))
                    and post_val != "-"
                    and total_all_post > 0
                ):
                    container["percentage"]["post"][col] = (
                        post_val / total_all_post
                    ) * 100
                else:
                    container["percentage"]["post"][col] = 0.0

    def _generate_summary_statistics(
        self, layer_summary: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary statistics for the layer analysis."""
        total_layers = len(layer_summary)

        if total_layers > 0:
            # Calculate mean pre/post across all layers (excluding dash values)
            layers_with_neurons = [
                layer for layer in layer_summary if layer["neuron_count"] > 0
            ]

            if layers_with_neurons:
                numeric_pre_values = [
                    layer["pre"]
                    for layer in layers_with_neurons
                    if isinstance(layer["pre"], (int, float))
                ]
                numeric_post_values = [
                    layer["post"]
                    for layer in layers_with_neurons
                    if isinstance(layer["post"], (int, float))
                ]

                mean_pre = (
                    sum(numeric_pre_values) / len(numeric_pre_values)
                    if numeric_pre_values
                    else 0.0
                )
                mean_post = (
                    sum(numeric_post_values) / len(numeric_post_values)
                    if numeric_post_values
                    else 0.0
                )
            else:
                mean_pre = 0.0
                mean_post = 0.0

            # Calculate total synapse counts for reference
            total_pre_synapses = sum(
                layer.get("total_pre", 0) for layer in layer_summary
            )
            total_post_synapses = sum(
                layer.get("total_post", 0) for layer in layer_summary
            )

            # Group by region for region-specific stats
            region_stats = {}
            for layer in layer_summary:
                region = layer["region"]
                if region not in region_stats:
                    region_stats[region] = {
                        "layers": 0,
                        "mean_pre": 0.0,
                        "mean_post": 0.0,
                        "total_pre": 0,
                        "total_post": 0,
                        "neuron_count": 0,
                        "sides": set(),
                    }
                region_stats[region]["layers"] += 1
                region_stats[region]["total_pre"] += layer.get("total_pre", 0)
                region_stats[region]["total_post"] += layer.get("total_post", 0)
                region_stats[region]["neuron_count"] += layer["neuron_count"]
                region_stats[region]["sides"].add(layer["side"])

            # Calculate mean per region
            for region in region_stats:
                if region_stats[region]["neuron_count"] > 0:
                    region_stats[region]["mean_pre"] = (
                        region_stats[region]["total_pre"]
                        / region_stats[region]["neuron_count"]
                    )
                    region_stats[region]["mean_post"] = (
                        region_stats[region]["total_post"]
                        / region_stats[region]["neuron_count"]
                    )
                else:
                    region_stats[region]["mean_pre"] = 0.0
                    region_stats[region]["mean_post"] = 0.0
                region_stats[region]["sides"] = sorted(
                    list(region_stats[region]["sides"])
                )
        else:
            mean_pre = 0.0
            mean_post = 0.0
            total_pre_synapses = 0
            total_post_synapses = 0
            region_stats = {}

        return {
            "total_layers": total_layers,
            "mean_pre": mean_pre,
            "mean_post": mean_post,
            "total_pre_synapses": total_pre_synapses,
            "total_post_synapses": total_post_synapses,
            "regions": region_stats,
        }
