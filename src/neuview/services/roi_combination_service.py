"""
ROI combination service for handling L/R ROI combination in combined pages.

This service modifies ROI innervation data for combined pages by merging entries
with the same ROI type but different sides (L/R) into single entries while
preserving the original data for individual side pages.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ROICombinationService:
    """
    Service for combining L/R ROI entries in combined pages.

    For combined pages (soma_side="combined"), this service:
    1. Merges ROI entries with same base name but different sides (L/R)
    2. Combines pre/post synapse counts and downstream/upstream counts
    3. Updates percentages based on combined totals
    4. Handles various ROI naming patterns

    For individual side pages (L/R/M), the original data is preserved unchanged.
    """

    # Patterns for detecting sided ROIs
    ROI_SIDE_PATTERNS = [
        r"^(.+)_([LR])$",  # ME_L, LO_R, etc.
        r"^(.+)\(([LR])\)$",  # ME(L), LO(R), etc.
        r"^(.+)_([LR])_(.+)$",  # ME_L_layer_1, LO_R_col_2, etc.
        r"^(.+)\(([LR])\)_(.+)$",  # ME(L)_layer_1, etc.
    ]

    def __init__(self):
        """Initialize the ROI combination service."""
        pass

    def process_roi_data_for_display(
        self, roi_summary: List[Dict[str, Any]], soma_side: str
    ) -> List[Dict[str, Any]]:
        """
        Process ROI summary data for display based on soma side.

        For combined pages, merges L/R entries for the same ROI base name.
        For individual side pages, returns original data unchanged.

        Args:
            roi_summary: List of ROI dictionaries from data processing service
            soma_side: Target soma side ("combined", "left", "right", "middle")

        Returns:
            Processed ROI summary appropriate for the soma side
        """
        if not roi_summary or soma_side != "combined":
            # For individual side pages, return original data
            return roi_summary

        logger.debug("Combining ROI data for combined page")

        # Group ROIs by base name (without side)
        roi_groups = self._group_rois_by_base_name(roi_summary)

        # Combine grouped ROIs
        combined_rois = []
        for base_name, rois in roi_groups.items():
            if len(rois) == 1:
                # Single ROI - remove side suffix for display
                roi = self._clean_single_roi_name(rois[0])
                combined_rois.append(roi)
            else:
                # Multiple ROIs - combine them
                combined_roi = self._merge_roi_group(base_name, rois)
                combined_rois.append(combined_roi)

        # Sort by total synapses (descending) and recalculate percentages
        combined_rois.sort(key=lambda x: x.get("total", 0), reverse=True)
        self._recalculate_percentages(combined_rois)

        return combined_rois

    def _group_rois_by_base_name(
        self, roi_summary: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group ROIs by their base name (without side suffix).

        Args:
            roi_summary: List of ROI dictionaries

        Returns:
            Dictionary mapping base names to lists of ROI entries
        """
        roi_groups = defaultdict(list)

        for roi in roi_summary:
            roi_name = roi.get("name", "")
            base_name = self._extract_base_name(roi_name)
            roi_groups[base_name].append(roi)

        return roi_groups

    def _extract_base_name(self, roi_name: str) -> str:
        """
        Extract base name from ROI name by removing side suffixes.

        Args:
            roi_name: Full ROI name (e.g., "ME_L", "LO(R)", "ME_L_layer_1")

        Returns:
            Base name without side (e.g., "ME", "LO", "ME_layer_1")
        """
        if not roi_name:
            return ""

        # Try each pattern to extract base name
        for pattern in self.ROI_SIDE_PATTERNS:
            match = re.match(pattern, roi_name)
            if match:
                groups = match.groups()
                if len(groups) == 2:  # Simple pattern: base_side
                    return groups[0]
                elif len(groups) == 3:  # Complex pattern: base_side_suffix
                    return f"{groups[0]}_{groups[2]}"

        # No side pattern found, return as-is
        return roi_name

    def _clean_single_roi_name(self, roi: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean single ROI entry by removing side suffix from name.

        Args:
            roi: ROI dictionary

        Returns:
            ROI dictionary with cleaned name
        """
        cleaned_roi = roi.copy()
        roi_name = roi.get("name", "")
        base_name = self._extract_base_name(roi_name)

        # Only update name if it actually changed (had a side)
        if base_name != roi_name:
            cleaned_roi["name"] = base_name

        return cleaned_roi

    def _merge_roi_group(
        self, base_name: str, rois: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge multiple ROI entries of the same base type.

        Args:
            base_name: Base ROI name (without side)
            rois: List of ROI entries to merge

        Returns:
            Single merged ROI entry
        """
        # Initialize combined entry
        combined = {
            "name": base_name,
            "pre": 0,
            "post": 0,
            "total": 0,
            "pre_percentage": 0,  # Will be recalculated later
            "post_percentage": 0,  # Will be recalculated later
            "downstream": 0,
            "upstream": 0,
        }

        # Combine counts from all ROI entries
        for roi in rois:
            combined["pre"] += roi.get("pre", 0)
            combined["post"] += roi.get("post", 0)
            combined["downstream"] += roi.get("downstream", 0)
            combined["upstream"] += roi.get("upstream", 0)

        combined["total"] = combined["pre"] + combined["post"]

        return combined

    def _recalculate_percentages(self, rois: List[Dict[str, Any]]) -> None:
        """
        Recalculate percentages based on combined totals.

        Args:
            rois: List of ROI dictionaries to update
        """
        if not rois:
            return

        # Calculate total pre and post synapses across all ROIs
        total_pre = sum(roi.get("pre", 0) for roi in rois)
        total_post = sum(roi.get("post", 0) for roi in rois)

        # Update percentages for each ROI
        for roi in rois:
            pre_count = roi.get("pre", 0)
            post_count = roi.get("post", 0)

            # Calculate pre percentage
            if total_pre > 0:
                roi["pre_percentage"] = (pre_count / total_pre) * 100
            else:
                roi["pre_percentage"] = 0.0

            # Calculate post percentage
            if total_post > 0:
                roi["post_percentage"] = (post_count / total_post) * 100
            else:
                roi["post_percentage"] = 0.0

    def get_roi_side_mapping(self, roi_name: str) -> List[str]:
        """
        Get possible sided versions of an ROI name.

        This is useful for neuroglancer integration where a combined ROI entry
        might need to map back to specific sided ROIs.

        Args:
            roi_name: Base ROI name (e.g., "ME", "LO_layer_1")

        Returns:
            List of possible sided ROI names
        """
        # Generate possible side variants
        side_variants = []

        # Simple suffixes
        side_variants.extend(
            [f"{roi_name}_L", f"{roi_name}_R", f"{roi_name}(L)", f"{roi_name}(R)"]
        )

        return side_variants

    def is_sided_roi(self, roi_name: str) -> bool:
        """
        Check if an ROI name contains side information.

        Args:
            roi_name: ROI name to check

        Returns:
            True if the ROI name contains side information
        """
        if not roi_name:
            return False

        # Check against all side patterns
        for pattern in self.ROI_SIDE_PATTERNS:
            if re.match(pattern, roi_name):
                return True

        return False

    def extract_side_from_roi(self, roi_name: str) -> Optional[str]:
        """
        Extract side information from ROI name.

        Args:
            roi_name: ROI name (e.g., "ME_L", "LO(R)")

        Returns:
            Side character ("L" or "R") or None if no side found
        """
        if not roi_name:
            return None

        # Try each pattern to extract side
        for pattern in self.ROI_SIDE_PATTERNS:
            match = re.match(pattern, roi_name)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    return groups[1]  # Side is always the second group

        return None

    def get_statistics(
        self, original_data: List[Dict[str, Any]], combined_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get statistics about the ROI combination process.

        Args:
            original_data: Original ROI summary data
            combined_data: Combined ROI summary data

        Returns:
            Dictionary with combination statistics
        """

        def count_sided_rois(data):
            sided = 0
            unsided = 0
            for roi in data:
                if self.is_sided_roi(roi.get("name", "")):
                    sided += 1
                else:
                    unsided += 1
            return {"sided": sided, "unsided": unsided, "total": sided + unsided}

        original_counts = count_sided_rois(original_data)
        combined_counts = count_sided_rois(combined_data)

        return {
            "original_rois": original_counts,
            "combined_rois": combined_counts,
            "reduction": original_counts["total"] - combined_counts["total"],
            "sided_rois_combined": original_counts["sided"] - combined_counts["sided"],
        }

