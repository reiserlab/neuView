"""
Cache Service for neuView.

This service handles all caching operations for neuron data, including
saving neuron type data and ROI hierarchy to persistent cache.
"""

import json
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
import pandas as pd

from ..models import (
    NeuronCollection,
    NeuronTypeName,
    Neuron,
    BodyId,
    SynapseCount,
    SomaSide,
)
from ..commands import GeneratePageCommand

logger = logging.getLogger(__name__)


class CacheService:
    """Service for handling all caching operations."""

    def __init__(
        self, cache_manager, page_generator=None, threshold_service=None, config=None
    ):
        """Initialize cache service.

        Args:
            cache_manager: Cache manager instance
            page_generator: Optional page generator for ROI data extraction
            threshold_service: Optional threshold service for configurable thresholds
            config: Configuration object for ROI hierarchy service
        """
        self.cache_manager = cache_manager
        self.page_generator = page_generator
        self.threshold_service = threshold_service
        self.config = config

        # Initialize threshold service if not provided
        if self.threshold_service is None:
            from .threshold_service import ThresholdService

            self.threshold_service = ThresholdService()

        # Initialize ROI hierarchy service for parent region lookup
        self.roi_hierarchy_service = None
        if self.config:
            from .roi_hierarchy_service import ROIHierarchyService

            self.roi_hierarchy_service = ROIHierarchyService(
                self.config, self.cache_manager
            )

    async def save_neuron_data_to_cache(
        self,
        neuron_type_name: str,
        neuron_data: dict,
        command: GeneratePageCommand,
        connector=None,
    ):
        """Save neuron data dictionary to persistent cache for later index generation.

        This method works with the modern dictionary format from get_neuron_data()
        and provides a direct caching approach for the page generation workflow.
        """
        if not self.cache_manager:
            return  # No cache manager available

        try:
            from ..cache import NeuronTypeCacheData

            # Save ROI hierarchy during generation to avoid queries during index creation
            await self.save_roi_hierarchy_to_cache()

            # Extract data from modern dictionary format
            neurons_df = neuron_data.get("neurons")
            connectivity_data = neuron_data.get("connectivity", {})
            summary_data = neuron_data.get("summary", {})

            # Convert DataFrame to NeuronCollection for enhanced cache processing
            neuron_collection = NeuronCollection(
                type_name=NeuronTypeName(neuron_type_name)
            )

            if neurons_df is not None and not neurons_df.empty:
                for _, row in neurons_df.iterrows():
                    # Extract soma side
                    soma_side = None
                    if "somaSide" in row and pd.notna(row["somaSide"]):
                        soma_side_val = row["somaSide"]
                        if soma_side_val == "L":
                            soma_side = SomaSide.LEFT
                        elif soma_side_val == "R":
                            soma_side = SomaSide.RIGHT
                        elif soma_side_val == "M":
                            soma_side = SomaSide.MIDDLE

                    # Create Neuron object
                    neuron = Neuron(
                        body_id=BodyId(int(row["bodyId"])),
                        type_name=NeuronTypeName(neuron_type_name),
                        instance=row.get("instance"),
                        status=row.get("status"),
                        soma_side=soma_side,
                        soma_x=row.get("somaLocation", {}).get("x")
                        if isinstance(row.get("somaLocation"), dict)
                        else None,
                        soma_y=row.get("somaLocation", {}).get("y")
                        if isinstance(row.get("somaLocation"), dict)
                        else None,
                        soma_z=row.get("somaLocation", {}).get("z")
                        if isinstance(row.get("somaLocation"), dict)
                        else None,
                        synapse_count=SynapseCount(
                            pre=int(row.get("pre", 0)), post=int(row.get("post", 0))
                        ),
                        cell_class=row.get("cellClass"),
                        cell_subclass=row.get("cellSubclass"),
                        cell_superclass=row.get("cellSuperclass"),
                    )
                    neuron_collection.add_neuron(neuron)

            # Extract ROI summary and parent ROIs from neuron data
            roi_summary = []
            parent_rois = []
            spatial_metrics = {
                side: {
                    region: {
                        "cols_innervated": None,
                        "coverage": None,
                        "cell_size": None,
                    }
                    for region in ["ME", "LO", "LOP"]
                }
                for side in ["L", "R", "both"]
            }

            # Get ROI data if available in the neuron data
            roi_counts_df = neuron_data.get("roi_counts")
            if (
                roi_counts_df is not None
                and not roi_counts_df.empty
                and self.page_generator
            ):
                try:
                    # Use the page generator's ROI aggregation method with correct connector
                    active_connector = connector or (
                        self.page_generator.connector
                        if hasattr(self.page_generator, "connector")
                        else None
                    )
                    if not active_connector:
                        logger.debug(
                            f"No connector available for ROI data extraction for {neuron_type_name}"
                        )
                        roi_summary = []
                        parent_rois = []
                    else:
                        roi_summary_full = self.page_generator._aggregate_roi_data(
                            roi_counts_df, neurons_df, "combined", active_connector
                        )

                        # Filter ROIs by threshold and clean names (same logic as IndexService)
                        threshold = self.threshold_service.get_roi_filtering_threshold()
                        threshold_high = self.threshold_service.get_roi_filtering_threshold(
                            profile_name="roi_filtering_strict"
                            )
                        cleaned_roi_summary = []
                        seen_names = set()

                        for roi in roi_summary_full:
                            if (
                                roi["pre_percentage"] >= threshold
                                or roi["post_percentage"] >= threshold
                            ):
                                # Clean ROI name for consistent display using ROI hierarchy service
                                clean_name = (
                                    self.roi_hierarchy_service._clean_roi_name(
                                        roi["name"]
                                    )
                                    if self.roi_hierarchy_service
                                    else roi["name"]
                                )
                                if clean_name not in seen_names:
                                    seen_names.add(clean_name)
                                    entry = {
                                            "name": clean_name,
                                            "pre_percentage": roi["pre_percentage"],
                                            "post_percentage": roi["post_percentage"],
                                            "total_synapses": roi["pre"] + roi["post"],
                                            "pre_synapses": roi["pre"],
                                            "post_synapses": roi["post"],
                                        }
                                    if clean_name in ["ME", "LO", "LOP"]:
                                        if (roi["pre_percentage"] >= threshold_high and (roi["pre"]+roi["post"])>50
                                            or roi["post_percentage"] >= threshold_high and (roi["pre"]+roi["post"])>50):
                                            include_in_scatter = 1
                                        else:
                                            include_in_scatter = 0
                                        entry["incl_scatter"] = include_in_scatter
                                    cleaned_roi_summary.append(entry)

                        roi_summary = cleaned_roi_summary

                        # Collect all parent ROIs from all ROIs with connections
                        parent_rois_set = set()
                        if (
                            roi_summary
                            and self.roi_hierarchy_service
                            and active_connector
                        ):
                            for roi_data in roi_summary:
                                roi_name = roi_data["name"]
                                parent_roi_temp = (
                                    self.roi_hierarchy_service.get_roi_hierarchy_parent(
                                        roi_name, active_connector
                                    )
                                )
                                if parent_roi_temp:
                                    parent_rois_set.add(parent_roi_temp)
                                else:
                                    # If no parent found, use the ROI name itself
                                    parent_rois_set.add(roi_name)
                        elif roi_summary:
                            # Fallback: if no hierarchy service, use ROI names directly
                            for roi_data in roi_summary:
                                parent_rois_set.add(roi_data["name"])

                        parent_rois = sorted(list(parent_rois_set))

                        # Calculate spatial metrics for columns if column ROIs are present.
                        # These metrics are calculated using synapses within the ROI from
                        # both L and R instances.
                        for side in ["L", "R"]:
                            for region in ["ME", "LO", "LOP"]:
                                str_pattern = f"{region}_{side}_col_"
                                col_df = roi_counts_df[
                                    roi_counts_df["roi"].str.contains(str_pattern)
                                ]
                                # Total number of columns innervated by cells from this cell type
                                spatial_metrics[side][region]["cols_innervated"] = (
                                    col_df["roi"].nunique()
                                )
                                if not col_df.empty:
                                    # coverage factor - number of cells per column
                                    spatial_metrics[side][region]["coverage"] = (
                                        col_df.groupby("roi")["bodyId"].nunique().mean()
                                    )
                                    # cell size - number of columns per cell
                                    spatial_metrics[side][region]["cell_size"] = (
                                        col_df.groupby("bodyId")["roi"]
                                        .nunique()
                                        .median()
                                    )
                        # Calculate the combined metrics as the mean of L and R values
                        for region in ["ME", "LO", "LOP"]:
                            for metric in ["cols_innervated", "coverage", "cell_size"]:
                                values = [
                                    v
                                    for v in (
                                        spatial_metrics["L"][region][metric],
                                        spatial_metrics["R"][region][metric],
                                    )
                                    if v is not None
                                ]
                                spatial_metrics["both"][region][metric] = (
                                    sum(values) / len(values) if values else None
                                )

                except Exception as e:
                    logger.warning(
                        f"Error processing ROI data for {neuron_type_name}: {e}"
                    )
                    roi_summary = []
                    parent_rois = []

            # Extract soma side counts from summary
            soma_side_counts = {
                "left": summary_data.get("left_count", 0),
                "right": summary_data.get("right_count", 0),
                "middle": summary_data.get("middle_count", 0),
                "total": summary_data.get("total_count", 0),
            }

            # Extract synapse stats
            avg_pre = summary_data.get("avg_pre_synapses", 0)
            avg_post = summary_data.get("avg_post_synapses", 0)
            synapse_stats = {
                "total_pre": summary_data.get("total_pre_synapses", 0),
                "total_post": summary_data.get("total_post_synapses", 0),
                "avg_pre": avg_pre,
                "avg_post": avg_post,
                "avg_total": avg_pre + avg_post,
            }

            # Extract available soma sides
            soma_sides_available = []
            if soma_side_counts["left"] > 0:
                soma_sides_available.append("left")
            if soma_side_counts["right"] > 0:
                soma_sides_available.append("right")
            if soma_side_counts["middle"] > 0:
                soma_sides_available.append("middle")
            if len(soma_sides_available) > 1:
                soma_sides_available.append("combined")

            # Create cache data object with correct parameters
            cache_data = NeuronTypeCacheData(
                neuron_type=neuron_type_name,
                total_count=summary_data.get("total_count", 0),
                soma_side_counts=soma_side_counts,
                synapse_stats=synapse_stats,
                roi_summary=roi_summary,
                parent_rois=parent_rois,
                generation_timestamp=time.time(),
                soma_sides_available=soma_sides_available,
                has_connectivity=bool(
                    connectivity_data.get("upstream")
                    or connectivity_data.get("downstream")
                ),
                metadata={"soma_side": neuron_data.get("soma_side", "combined")},
                consensus_nt=summary_data.get("consensus_nt"),
                celltype_predicted_nt=summary_data.get("celltype_predicted_nt"),
                celltype_predicted_nt_confidence=summary_data.get(
                    "celltype_predicted_nt_confidence"
                ),
                celltype_total_nt_predictions=summary_data.get(
                    "celltype_total_nt_predictions"
                ),
                cell_class=summary_data.get("cell_class"),
                cell_subclass=summary_data.get("cell_subclass"),
                cell_superclass=summary_data.get("cell_superclass"),
                nt_analysis=summary_data.get("nt_analysis"),
                original_neuron_name=neuron_type_name,
                dimorphism=summary_data.get("dimorphism"),
                synonyms=summary_data.get("synonyms"),
                flywire_types=summary_data.get("flywire_types"),
                soma_neuromere=summary_data.get("somaNeuromere"),
                truman_hl=summary_data.get("trumanHl"),
                spatial_metrics=spatial_metrics,
            )

            # Save to cache
            self.cache_manager.save_neuron_type_cache(cache_data)
            logger.debug(
                f"Saved {neuron_type_name} to persistent cache with {len(roi_summary)} ROIs"
            )

        except Exception as e:
            logger.warning(f"Failed to save {neuron_type_name} to cache: {e}")
            # Don't fail the whole operation for cache issues

    async def save_roi_hierarchy_to_cache(self):
        """Save ROI hierarchy to cache during generation to avoid queries during index creation."""
        try:
            # Check if ROI hierarchy is already cached
            if self.cache_manager and self.cache_manager.load_roi_hierarchy():
                logger.debug("ROI hierarchy already cached, skipping fetch")
                return

            logger.debug("Fetching ROI hierarchy from database for caching")
            # Use the existing connector's method to fetch ROI hierarchy
            if (
                hasattr(self.page_generator, "connector")
                and self.page_generator.connector
            ):
                hierarchy_data = self.page_generator.connector._get_roi_hierarchy()
            else:
                logger.debug("No connector available for fetching ROI hierarchy")
                return

            # Save to cache
            if hierarchy_data and self.cache_manager:
                success = self.cache_manager.save_roi_hierarchy(hierarchy_data)
                if success:
                    logger.info(
                        "✅ Saved ROI hierarchy to cache during generation - will speed up index creation"
                    )
                else:
                    logger.warning("Failed to save ROI hierarchy to cache")

        except Exception as e:
            logger.debug(f"Failed to cache ROI hierarchy during generation: {e}")

    def _clean_roi_name(self, roi_name: str) -> str:
        """Remove (R), (L), _R, _L suffixes from ROI names to merge left/right regions."""
        import re

        # Remove (R), (L), or (M) suffixes from ROI names (parenthetical format)
        cleaned = re.sub(r"\s*\([RLM]\)$", "", roi_name)

        # Also remove _R, _L, or _M suffixes from ROI names (underscore format)
        # This handles FAFB patterns like OL_R and OL_L, treating them both as "OL"
        cleaned = re.sub(r"_[RLM]$", "", cleaned)

        return cleaned.strip()

    def _get_roi_hierarchy_parent(self, roi_name: str, connector=None) -> str:
        """Get the parent ROI of the given ROI from the hierarchy."""
        try:
            # Load ROI hierarchy from cache or fetch if needed
            hierarchy_data = None
            if self.cache_manager:
                hierarchy_data = self.cache_manager.load_roi_hierarchy()

            if not hierarchy_data and connector:
                # Fetch from database using provided connector
                hierarchy_data = connector._get_roi_hierarchy()

            if not hierarchy_data:
                return ""

            # Clean the ROI name first (remove (R), (L), (M) suffixes)
            cleaned_roi = self._clean_roi_name(roi_name)

            # Search recursively for the ROI and its parent
            parent = self._find_roi_parent_recursive(cleaned_roi, hierarchy_data)
            return parent if parent else ""

        except Exception as e:
            logger.debug(f"Failed to get parent ROI for {roi_name}: {e}")
            return ""

    def load_persistent_columns_cache(
        self, cache_key: str
    ) -> Optional[Tuple[list, Dict[str, set]]]:
        """
        Load persistent cache for all columns dataset query.

        Args:
            cache_key: Unique key for the cache entry

        Returns:
            Tuple of (all_columns, region_map) if cache is valid, None otherwise
        """
        try:
            # Create cache directory
            cache_dir = Path("output/.cache")
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Use hash of cache key for filename to avoid filesystem issues
            cache_filename = (
                hashlib.md5(cache_key.encode()).hexdigest() + "_columns.json"
            )
            cache_file = cache_dir / cache_filename

            if cache_file.exists():
                with open(cache_file, "r") as f:
                    data = json.load(f)

                # Check cache age (expire after 24 hours)
                cache_age = time.time() - data.get("timestamp", 0)
                if cache_age < 86400:  # 24 hours
                    # Reconstruct the tuple from JSON
                    all_columns = data["all_columns"]
                    region_map = {}
                    for region, coords_list in data["region_map"].items():
                        region_map[region] = set(tuple(coord) for coord in coords_list)

                    logger.info(
                        f"Loaded {len(all_columns)} columns from persistent cache (age: {cache_age / 3600:.1f}h)"
                    )
                    return (all_columns, region_map)
                else:
                    logger.info("Persistent columns cache expired, will refresh")
                    cache_file.unlink()

        except Exception as e:
            logger.warning(f"Failed to load persistent columns cache: {e}")

        return None

    def save_persistent_columns_cache(
        self, cache_key: str, all_columns: list, region_map: Dict[str, set]
    ):
        """
        Save columns data to persistent cache.

        Args:
            cache_key: Unique key for the cache entry
            all_columns: List of column data
            region_map: Dictionary mapping regions to coordinate sets
        """
        try:
            # Create cache directory
            cache_dir = Path("output/.cache")
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Use hash of cache key for filename to avoid filesystem issues
            cache_filename = (
                hashlib.md5(cache_key.encode()).hexdigest() + "_columns.json"
            )
            cache_file = cache_dir / cache_filename

            # Convert sets to lists for JSON serialization
            serializable_region_map = {}
            for region, coords_set in region_map.items():
                serializable_region_map[region] = list(coords_set)

            data = {
                "timestamp": time.time(),
                "all_columns": all_columns,
                "region_map": serializable_region_map,
            }

            with open(cache_file, "w") as f:
                json.dump(data, f)

            logger.info(f"Saved {len(all_columns)} columns to persistent cache")

        except Exception as e:
            logger.warning(f"Failed to save persistent columns cache: {e}")

    def get_columns_from_neuron_cache(
        self, neuron_type: str
    ) -> Tuple[Optional[list], Optional[Dict[str, set]]]:
        """
        Extract column data from neuron type cache if available.

        Args:
            neuron_type: The neuron type to get cached column data for

        Returns:
            Tuple of (columns_data, region_columns_map) or (None, None) if not cached
        """
        try:
            if self.cache_manager is not None:
                cache_data = self.cache_manager.load_neuron_type_cache(neuron_type)
                if (
                    cache_data
                    and cache_data.columns_data
                    and cache_data.region_columns_map
                ):
                    # Convert region_columns_map back to sets from lists
                    region_map = {}
                    for region, coords_list in cache_data.region_columns_map.items():
                        region_map[region] = set(tuple(coord) for coord in coords_list)

                    logger.debug(
                        f"Retrieved column data from cache for {neuron_type}: {len(cache_data.columns_data)} columns"
                    )
                    return cache_data.columns_data, region_map
        except Exception as e:
            logger.debug(f"Failed to get column data from cache for {neuron_type}: {e}")

        return None, None

    def _find_roi_parent_recursive(
        self, roi_name: str, hierarchy: dict, parent_name: str = ""
    ) -> str:
        """Recursively search for ROI in hierarchy and return its parent."""
        for key, value in hierarchy.items():
            # Direct match
            if key == roi_name:
                return parent_name

            # Handle ROI naming variations:
            # - Remove side suffixes: "AOTU(L)*" -> "AOTU"
            # - Remove asterisks: "AOTU*" -> "AOTU"
            cleaned_key = (
                key.replace("(L)", "")
                .replace("(R)", "")
                .replace("(M)", "")
                .replace("*", "")
                .strip()
            )
            if cleaned_key == roi_name:
                return parent_name

            # Also check if the ROI name matches the beginning of the key
            if key.startswith(roi_name) and (
                len(key) == len(roi_name) or key[len(roi_name)] in "(*"
            ):
                return parent_name

            # Recursive search
            if isinstance(value, dict):
                result = self._find_roi_parent_recursive(roi_name, value, key)
                if result:
                    return result
        return ""
