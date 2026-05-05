"""
ROI Analysis Service

Handles ROI summary analysis for neuron types, including ROI data aggregation
and parent ROI determination.
"""

import re
import logging
from typing import List, Tuple, Dict, Any, Set
from .roi_hierarchy_service import ROIHierarchyService
from ..config import Config

logger = logging.getLogger(__name__)


class ROIAnalysisService:
    """Service for analyzing ROI data and generating summaries for neuron types.

    Args:
        page_generator: Optional page generator for ROI data extraction.
        roi_hierarchy_service: Service for managing ROI hierarchy data.
    """

    def __init__(self, page_generator=None, roi_hierarchy_service=None):
        self.config = Config.load("config.yaml")
        self.page_generator = page_generator
        self.roi_hierarchy_service = roi_hierarchy_service
        self._parent_roi_cache: Dict[str, str] = {}

        # Initialize ROI hierarchy service for parent region lookup
        if roi_hierarchy_service is None:
            self.roi_hierarchy_service = ROIHierarchyService(self.config)

    def get_roi_summary_for_neuron_type(
        self, neuron_type: str, connector, skip_roi_analysis=False
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Get ROI summary for a specific neuron type."""
        # Skip expensive ROI analysis if requested for faster indexing
        if skip_roi_analysis:
            return [], ""

        try:
            # Get neuron data for all sides
            neuron_data = connector.get_neuron_data(neuron_type, soma_side="combined")

            roi_counts = neuron_data.get("roi_counts")
            neurons = neuron_data.get("neurons")

            if (
                not neuron_data
                or roi_counts is None
                or roi_counts.empty
                or neurons is None
                or neurons.empty
            ):
                return [], ""

            # Use the data processing service for ROI aggregation
            from .data_processing_service import DataProcessingService

            data_processing_service = DataProcessingService(self.page_generator)
            roi_summary = data_processing_service.aggregate_roi_data(
                neuron_data.get("roi_counts"),
                neuron_data.get("neurons"),
                "combined",
                connector,
            )

            # Filter ROIs by threshold and clean names
            # Only show ROIs with configurable threshold of either input (post) or output (pre) connections
            # This ensures only significant innervation targets are displayed
            from .threshold_service import ThresholdService

            threshold_service = ThresholdService()
            threshold = (
                threshold_service.get_roi_filtering_threshold()
            )  # Configurable percentage threshold for ROI significance
            cleaned_roi_summary = []
            seen_names = set()

            for roi in roi_summary:
                # Only include ROIs that pass the 1.5% threshold for input OR output
                if (
                    roi["pre_percentage"] >= threshold
                    or roi["post_percentage"] >= threshold
                ):
                    cleaned_name = self.roi_hierarchy_service._clean_roi_name(
                        roi["name"]
                    )
                    if cleaned_name and cleaned_name not in seen_names:
                        cleaned_roi_summary.append(
                            {
                                "name": cleaned_name,
                                "total": roi["total"],
                                "pre_percentage": roi["pre_percentage"],
                                "post_percentage": roi["post_percentage"],
                            }
                        )
                        seen_names.add(cleaned_name)

                        if len(cleaned_roi_summary) >= 5:  # Limit to top 5
                            break

            # Get parent ROI for the highest ranking (first) ROI
            parent_roi = ""
            if cleaned_roi_summary:
                highest_roi = cleaned_roi_summary[0]["name"]
                parent_roi = self.roi_hierarchy_service.get_roi_hierarchy_parent(
                    highest_roi, connector
                )

            # cache the parent_roi
            try:
                self._parent_roi_cache[neuron_type] = parent_roi or ""
            except Exception as _:
                pass

            return cleaned_roi_summary, parent_roi

        except Exception as e:
            # If there's any error fetching ROI data, return empty list and parent
            logger.warning(f"Failed to get ROI summary for {neuron_type}: {e}")
            return [], ""

    def collect_filter_options_from_index_data(
        self, index_data: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Collect filter options from neuron data for the index page."""
        roi_options = set()
        region_options = set()
        nt_options = set()
        superclass_options = set()
        class_options = set()
        subclass_options = set()
        dimorphism_options = set()
        soma_neuromere_options = set()
        truman_hl_options = set()

        for entry in index_data:
            # Collect ROIs from roi_summary
            if entry.get("roi_summary"):
                for roi_info in entry["roi_summary"]:
                    if isinstance(roi_info, dict) and "name" in roi_info:
                        roi_name = roi_info["name"]
                        if roi_name and roi_name.strip():
                            roi_options.add(roi_name.strip())

            # Collect regions from parent_rois
            parent_rois = entry.get("parent_rois", [])
            if parent_rois:
                for parent_roi in parent_rois:
                    if parent_roi and parent_roi.strip():
                        # Clean region name by removing side suffixes
                        clean_parent_roi = self.roi_hierarchy_service._clean_roi_name(
                            parent_roi.strip()
                        )
                        if clean_parent_roi:
                            region_options.add(clean_parent_roi)

            # Collect neurotransmitters
            if entry.get("consensus_nt") and entry["consensus_nt"].strip():
                nt_options.add(entry["consensus_nt"].strip())
            elif (
                entry.get("celltype_predicted_nt")
                and entry["celltype_predicted_nt"].strip()
            ):
                nt_options.add(entry["celltype_predicted_nt"].strip())

            # Class hierarchy + soma neuromere + truman hl are lists since
            # cells in the same celltype may carry different values.
            list_field_targets = (
                ("cell_superclass", superclass_options),
                ("cell_class", class_options),
                ("cell_subclass", subclass_options),
                ("soma_neuromere", soma_neuromere_options),
                ("truman_hl", truman_hl_options),
            )
            for key, target in list_field_targets:
                for value in entry.get(key) or []:
                    if value and value.strip():
                        target.add(value.strip())

            # Collect dimorphism
            if entry.get("dimorphism") and entry["dimorphism"].strip():
                dimorphism_options.add(entry["dimorphism"].strip())

        # Sort filter options
        sorted_roi_options = sorted(roi_options)
        sorted_region_options = sorted(region_options)
        # Put 'Other' at the end if it exists
        if "Other" in sorted_region_options:
            sorted_region_options.remove("Other")
            sorted_region_options.append("Other")

        return {
            "rois": sorted_roi_options,
            "regions": sorted_region_options,
            "neurotransmitters": sorted(nt_options),
            "superclasses": sorted(superclass_options),
            "classes": sorted(class_options),
            "subclasses": sorted(subclass_options),
            "dimorphisms": sorted(dimorphism_options),
            "soma_neuromeres": sorted(soma_neuromere_options),
            "truman_hls": sorted(truman_hl_options),
        }

    def calculate_cell_count_ranges(
        self, index_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate cell count ranges using fixed values for filtering."""
        cell_count_ranges = []
        if index_data:
            # Extract all cell counts
            cell_counts = [
                entry["total_count"]
                for entry in index_data
                if entry.get("total_count", 0) > 0
            ]

            if cell_counts:
                # Define fixed ranges: 1, 2, 3, 4, 5, 6-10, 10-50, 50-100, 100-500, 500-1000, 1000-2000, 2000-5000, >5000
                fixed_ranges = [
                    {"lower": 1, "upper": 1, "label": "1", "value": "1-1"},
                    {"lower": 2, "upper": 2, "label": "2", "value": "2-2"},
                    {"lower": 3, "upper": 3, "label": "3", "value": "3-3"},
                    {"lower": 4, "upper": 4, "label": "4", "value": "4-4"},
                    {"lower": 5, "upper": 5, "label": "5", "value": "5-5"},
                    {"lower": 6, "upper": 10, "label": "6-10", "value": "6-10"},
                    {"lower": 10, "upper": 50, "label": "10-50", "value": "10-50"},
                    {"lower": 50, "upper": 100, "label": "50-100", "value": "50-100"},
                    {
                        "lower": 100,
                        "upper": 500,
                        "label": "100-500",
                        "value": "100-500",
                    },
                    {
                        "lower": 500,
                        "upper": 1000,
                        "label": "500-1000",
                        "value": "500-1000",
                    },
                    {
                        "lower": 1000,
                        "upper": 2000,
                        "label": "1000-2000",
                        "value": "1000-2000",
                    },
                    {
                        "lower": 2000,
                        "upper": 5000,
                        "label": "2000-5000",
                        "value": "2000-5000",
                    },
                    {
                        "lower": 5001,
                        "upper": float("inf"),
                        "label": ">5000",
                        "value": "5001-999999",
                    },
                ]

                # Only include ranges that contain actual data
                for range_def in fixed_ranges:
                    has_data = any(
                        range_def["lower"] <= count <= range_def["upper"]
                        for count in cell_counts
                    )
                    if has_data:
                        cell_count_ranges.append(range_def)

        return cell_count_ranges

    def get_all_dataset_layers(
        self, layer_pattern: str, connector
    ) -> List[Tuple[str, str, int]]:
        """
        Query the entire dataset for all available layer patterns.

        Args:
            layer_pattern: Regex pattern to match layer ROIs
            connector: NeuPrint connector to query the database

        Returns:
            List of tuples: (region, side, layer_num) for all layers in dataset
        """
        try:
            # Get all ROI names from cached hierarchy
            roi_hierarchy = connector._get_roi_hierarchy()
            all_rois = []

            if roi_hierarchy:
                all_rois = self.extract_roi_names_from_hierarchy(roi_hierarchy)

            # Fallback: query database directly if hierarchy fails
            if not all_rois:
                query = """
                MATCH (r:Roi)
                RETURN r.name as roi
                ORDER BY r.name
                """
                result = connector.client.fetch_custom(query)
                if hasattr(result, "iterrows"):
                    all_rois = [record["roi"] for _, record in result.iterrows()]

            # Extract layer patterns from all ROIs
            all_dataset_layers = []
            for roi in all_rois:
                match = re.match(layer_pattern, roi)
                if match:
                    region = match.group(1)
                    side = match.group(2)
                    layer_num = int(match.group(3))
                    layer_key = (region, side, layer_num)
                    if layer_key not in all_dataset_layers:
                        all_dataset_layers.append(layer_key)

            return sorted(all_dataset_layers)

        except Exception as e:
            logger.warning(f"Could not query dataset for all layers: {e}")
            # Fallback: return empty list, will use only layers from current neuron
            return []

    def extract_roi_names_from_hierarchy(self, hierarchy, roi_names=None) -> Set[str]:
        """
        Recursively extract all ROI names from the hierarchical dictionary structure.

        Args:
            hierarchy: Dictionary or any structure from fetch_roi_hierarchy
            roi_names: Set to collect ROI names (used for recursion)

        Returns:
            Set of all ROI names found in the hierarchy
        """
        if roi_names is None:
            roi_names = set()

        if isinstance(hierarchy, dict):
            # Add all dictionary keys as potential ROI names
            for key in hierarchy.keys():
                if isinstance(key, str):
                    roi_names.add(key)

            # Recursively process all dictionary values
            for value in hierarchy.values():
                self.extract_roi_names_from_hierarchy(value, roi_names)

        elif isinstance(hierarchy, (list, tuple)):
            # Process each item in the list/tuple
            for item in hierarchy:
                self.extract_roi_names_from_hierarchy(item, roi_names)

        return roi_names

    def get_primary_rois(self, connector) -> Set[str]:
        """Get primary ROIs based on dataset type and available data."""
        primary_rois = set()

        # First, try to get primary ROIs from NeuPrint if we have a connector
        if connector and hasattr(connector, "client") and connector.client:
            try:
                # Get ROI hierarchy from cached connector method
                roi_hierarchy = connector._get_roi_hierarchy()

                if roi_hierarchy is not None:
                    # Extract all ROI names from the hierarchical dictionary structure
                    extracted_rois = self.extract_roi_names_from_hierarchy(
                        roi_hierarchy
                    )

                    # Filter for ROIs that have a star (*) and remove the star for display
                    for roi_name in extracted_rois:
                        if roi_name.endswith("*"):
                            # Remove the star and add to primary ROIs set
                            clean_roi_name = roi_name.rstrip("*")
                            primary_rois.add(clean_roi_name)

            except Exception as e:
                logger.warning(f"Could not fetch primary ROIs from NeuPrint: {e}")

        # Dataset-specific primary ROIs based on dataset name
        dataset_name = ""
        if connector and hasattr(connector, "config"):
            dataset_name = connector.config.neuprint.dataset.lower()

        # Add dataset-specific primary ROIs
        if "optic" in dataset_name or "ol" in dataset_name:
            # Optic-lobe specific primary ROIs
            optic_primary = {
                "ME(R)",
                "ME(L)",
                "LO(R)",
                "LO(L)",
                "LOP(R)",
                "LOP(L)",
                "AME(R)",
                "AME(L)",
                "LA(R)",
                "LA(L)",
            }
            primary_rois.update(optic_primary)
        elif "cns" in dataset_name:
            # CNS specific primary ROIs
            cns_primary = {
                "ME(R)",
                "ME(L)",
                "LO(R)",
                "LO(L)",
                "AL(R)",
                "AL(L)",
                "MB(R)",
                "MB(L)",
                "CX",
                "PB",
                "FB",
                "EB",
            }
            primary_rois.update(cns_primary)
        elif "hemibrain" in dataset_name:
            # Hemibrain specific primary ROIs
            hemibrain_primary = {
                "ME(R)",
                "ME(L)",
                "LO(R)",
                "LO(L)",
                "LOP(R)",
                "LOP(L)",
                "AL(R)",
                "AL(L)",
                "MB(R)",
                "MB(L)",
                "CX",
                "PB",
                "FB",
                "EB",
                "NO",
            }
            primary_rois.update(hemibrain_primary)

        # If we still have no primary ROIs, use a comprehensive fallback
        if len(primary_rois) == 0:
            primary_rois = {
                "ME(R)",
                "ME(L)",
                "LO(R)",
                "LO(L)",
                "LOP(R)",
                "LOP(L)",
                "AL(R)",
                "AL(L)",
                "MB(R)",
                "MB(L)",
                "CX",
                "PB",
                "FB",
                "EB",
                "NO",
                "BU(R)",
                "BU(L)",
                "LAL(R)",
                "LAL(L)",
                "ICL(R)",
                "ICL(L)",
                "IB",
                "ATL(R)",
                "ATL(L)",
            }

        return primary_rois

    def get_columns_for_neuron_type(
        self, connector, neuron_type: str
    ) -> Tuple[List[Dict], Dict[str, Set[Tuple]]]:
        """
        Query the dataset to get column coordinates that exist for a specific neuron type.
        This optimized version only processes the requested neuron type instead of all neurons.

        Args:
            connector: NeuPrint connector instance for database queries
            neuron_type: Specific neuron type to analyze

        Returns:
            Tuple of (type_columns, region_columns_map) where:
            - type_columns: List of dicts with hex1, hex2 (integers) for this type
            - region_columns_map: Dict mapping region_side names to sets of (hex1, hex2) tuples
        """
        import time

        start_time = time.time()

        # Define cache key for this analysis
        cache_key = f"columns_{neuron_type}"

        # Check if page_generator has in-memory cache
        if self.page_generator and hasattr(
            self.page_generator, "_neuron_type_columns_cache"
        ):
            if cache_key in self.page_generator._neuron_type_columns_cache:
                logger.info(
                    f"get_columns_for_neuron_type({neuron_type}): returning in-memory cached result"
                )
                return self.page_generator._neuron_type_columns_cache[cache_key]

        # Check persistent neuron cache second
        if (
            hasattr(self.page_generator, "cache_service")
            and self.page_generator.cache_service
        ):
            cached_columns, cached_region_map = (
                self.page_generator.cache_service.get_columns_from_neuron_cache(
                    neuron_type
                )
            )
            if cached_columns is not None and cached_region_map is not None:
                result_tuple = (cached_columns, cached_region_map)
                # Store in memory cache for future calls
                if self.page_generator and not hasattr(
                    self.page_generator, "_neuron_type_columns_cache"
                ):
                    self.page_generator._neuron_type_columns_cache = {}
                if self.page_generator:
                    self.page_generator._neuron_type_columns_cache[cache_key] = (
                        result_tuple
                    )
                logger.info(
                    f"get_columns_for_neuron_type({neuron_type}): returning persistent cached result"
                )
                return result_tuple

        try:
            # Optimized query for specific neuron type only
            escaped_type = connector._escape_for_cypher_string(neuron_type)
            query = f"""
                MATCH (n:Neuron)
                WHERE n.type = "{escaped_type}" AND n.roiInfo IS NOT NULL
                WITH n, apoc.convert.fromJsonMap(n.roiInfo) as roiData
                UNWIND keys(roiData) as roiName
                WITH roiName, roiData[roiName] as roiInfo
                WHERE roiName =~ '^(ME|LO|LOP)_[RL]_col_[A-Za-z0-9]+_[A-Za-z0-9]+$'
                AND (roiInfo.pre > 0 OR roiInfo.post > 0)
                WITH roiName,
                     SUM(COALESCE(roiInfo.pre, 0)) as total_pre,
                     SUM(COALESCE(roiInfo.post, 0)) as total_post
                RETURN roiName as roi, total_pre as pre, total_post as post
                ORDER BY roi
            """

            result = connector.client.fetch_custom(query)
            query_time = time.time() - start_time

            if result is None or result.empty:
                logger.info(
                    f"get_columns_for_neuron_type({neuron_type}): no columns found in {query_time:.3f}s"
                )
                return [], {}

            # Parse ROI data to extract coordinates
            column_pattern = r"^(ME|LO|LOP)_([RL])_col_([A-Za-z0-9]+)_([A-Za-z0-9]+)$"
            column_data = {}
            coordinate_strings = {}

            for _, row in result.iterrows():
                match = re.match(column_pattern, row["roi"])
                if match:
                    region, side, coord1, coord2 = match.groups()

                    # Parse coordinates
                    try:
                        hex1_dec = int(coord1) if coord1.isdigit() else int(coord1, 16)
                        hex2_dec = int(coord2) if coord2.isdigit() else int(coord2, 16)
                    except ValueError:
                        continue

                    coord_key = (hex1_dec, hex2_dec)
                    if coord_key not in column_data:
                        column_data[coord_key] = set()
                    column_data[coord_key].add(f"{region}_{side}")
                    coordinate_strings[coord_key] = (coord1, coord2)

            # Build region columns map
            region_columns_map = {
                "ME_L": set(),
                "LO_L": set(),
                "LOP_L": set(),
                "ME_R": set(),
                "LO_R": set(),
                "LOP_R": set(),
                "ME": set(),
                "LO": set(),
                "LOP": set(),
            }

            for coord_key, region_sides in column_data.items():
                for region_side in region_sides:
                    region_columns_map[region_side].add(coord_key)

            # Build columns list
            type_columns = []
            for coord_key in sorted(column_data.keys()):
                hex1_dec, hex2_dec = coord_key
                type_columns.append({"hex1": hex1_dec, "hex2": hex2_dec})

            # Cache the result
            if self.page_generator and not hasattr(
                self.page_generator, "_neuron_type_columns_cache"
            ):
                self.page_generator._neuron_type_columns_cache = {}

            result_tuple = (type_columns, region_columns_map)
            if self.page_generator:
                cache_key = f"columns_{neuron_type}"
                self.page_generator._neuron_type_columns_cache[cache_key] = result_tuple

            logger.info(
                f"get_columns_for_neuron_type({neuron_type}): found {len(type_columns)} columns in {time.time() - start_time:.3f}s"
            )
            return result_tuple

        except Exception as e:
            logger.warning(f"Could not query columns for {neuron_type}: {e}")
            return [], {}

    def get_region_for_type(self, neuron_type: str, connector) -> str:
        """
        Get the primary region assignment for a neuron type.

        Args:
            neuron_type: Name of the neuron type
            connector: Database connector

        Returns:
            Primary region name for the neuron type
        """
        try:
            # 1) In-memory cache
            parent_roi = self._parent_roi_cache.get(neuron_type)
            if parent_roi is not None:
                return parent_roi

            # 2) Fallback: compute via the existing ROI analysis path (once)
            #    This will also populate the caches because of the change above.
            _roi_summary, parent_roi = self.get_roi_summary_for_neuron_type(
                neuron_type,
                connector,
                skip_roi_analysis=False,
            )
            return parent_roi or ""

        except Exception as e:
            logger.warning(f"Could not determine region for {neuron_type}: {e}")
            return ""
