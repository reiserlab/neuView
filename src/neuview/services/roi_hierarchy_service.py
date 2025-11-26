"""
ROI Hierarchy Service

Handles ROI hierarchy caching, parent lookup logic, and ROI data management.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class ROIHierarchyService:
    """Service for managing ROI hierarchy data and caching."""

    def __init__(self, config, cache_manager=None):
        self.config = config
        self.cache_manager = cache_manager
        self._roi_hierarchy_cache = None
        self._roi_parent_cache = {}
        self._persistent_roi_cache_path = None

    def _clean_roi_name(self, roi_name: str) -> str:
        """Remove (R), (L), _R, _L suffixes from ROI names to merge left/right regions."""
        import re

        # Remove (R), (L), or (M) suffixes from ROI names (parenthetical format)
        cleaned = re.sub(r"\s*\([RLM]\)$", "", roi_name)

        # Also remove _R, _L, or _M suffixes from ROI names (underscore format)
        # This handles FAFB patterns like OL_R and OL_L, treating them both as "OL"
        cleaned = re.sub(r"_[RLM]$", "", cleaned)

        return cleaned.strip()

    def _find_roi_parent_recursive(
        self, target_roi: str, current_dict: dict, parent_name: str = ""
    ) -> str:
        """Recursively search for ROI in hierarchy and return its parent."""
        for key, value in current_dict.items():
            cleaned_key = self._clean_roi_name(key.rstrip("*"))  # Remove stars too

            # If we found our target ROI, return the parent
            if cleaned_key == target_roi:
                return parent_name

            # If this is a dictionary, search recursively
            if isinstance(value, dict):
                result = self._find_roi_parent_recursive(target_roi, value, cleaned_key)
                if result:
                    return result

        return ""

    def get_roi_hierarchy_cached(self, connector, output_dir=None):
        """Get ROI hierarchy with persistent caching to avoid repeated expensive fetches."""
        if self._roi_hierarchy_cache is None:
            # Try to load from cache manager first
            if self.cache_manager:
                self._roi_hierarchy_cache = self.cache_manager.load_roi_hierarchy()
                if self._roi_hierarchy_cache:
                    logger.info("Loaded ROI hierarchy from cache manager")
                    return self._roi_hierarchy_cache

            # Fallback to old persistent cache system
            # Set cache path based on output directory
            if output_dir and not self._persistent_roi_cache_path:
                cache_dir = Path(output_dir) / ".cache"
                cache_dir.mkdir(exist_ok=True)
                self._persistent_roi_cache_path = cache_dir / "roi_hierarchy.json"
            elif not self._persistent_roi_cache_path:
                # Fallback to default output directory
                cache_dir = Path(self.config.output.directory) / ".cache"
                cache_dir.mkdir(exist_ok=True)
                self._persistent_roi_cache_path = cache_dir / "roi_hierarchy.json"

            # Try to load from persistent cache first
            self._roi_hierarchy_cache = self._load_persistent_roi_cache()

            if not self._roi_hierarchy_cache:
                # Cache miss - fetch from database
                logger.info("ROI hierarchy not found in cache, fetching from database")
                try:
                    # Use connector's cached ROI hierarchy method
                    self._roi_hierarchy_cache = connector._get_roi_hierarchy()

                    # Save to cache systems
                    self._save_persistent_roi_cache(self._roi_hierarchy_cache)
                    if self.cache_manager:
                        self.cache_manager.save_roi_hierarchy(self._roi_hierarchy_cache)

                except Exception:
                    self._roi_hierarchy_cache = {}
            else:
                logger.info("Loaded ROI hierarchy from persistent cache")

        return self._roi_hierarchy_cache

    def get_roi_hierarchy_parent(self, roi_name: str, connector) -> str:
        """Get the parent ROI of the given ROI from the hierarchy."""
        # Check cache first
        if roi_name in self._roi_parent_cache:
            return self._roi_parent_cache[roi_name]

        try:
            hierarchy = self.get_roi_hierarchy_cached(connector)
            if not hierarchy:
                self._roi_parent_cache[roi_name] = ""
                return ""

            # Clean the ROI name first (remove (R), (L), (M) suffixes)
            cleaned_roi = self._clean_roi_name(roi_name)

            # Search recursively for the ROI and its parent
            parent = self._find_roi_parent_recursive(cleaned_roi, hierarchy)
            result = parent if parent else ""

            # Cache the result
            self._roi_parent_cache[roi_name] = result
            return result
        except Exception:
            # If any error occurs, cache empty result and return
            self._roi_parent_cache[roi_name] = ""
            return ""

    def _load_persistent_roi_cache(self):
        """Load ROI hierarchy from persistent cache file."""
        try:
            if not self._persistent_roi_cache_path:
                return {}

            cache_path = Path(self._persistent_roi_cache_path)
            if cache_path.exists():
                with open(cache_path, "r") as f:
                    cache_data = json.load(f)

                # Check if cache is still valid (e.g., less than 24 hours old)
                cache_age = time.time() - cache_data.get("timestamp", 0)
                if cache_age < 24 * 3600:  # 24 hours
                    logger.info("Loaded ROI hierarchy from persistent cache")
                    return cache_data.get("hierarchy", {})
                else:
                    logger.info("Persistent ROI cache expired")

        except Exception as e:
            logger.debug(f"Failed to load persistent ROI cache: {e}")

        return {}

    def _save_persistent_roi_cache(self, hierarchy):
        """Save ROI hierarchy to persistent cache file."""
        try:
            if not self._persistent_roi_cache_path:
                return

            cache_path = Path(self._persistent_roi_cache_path)
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {"hierarchy": hierarchy, "timestamp": time.time()}

            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)

            logger.info(f"Saved ROI hierarchy to persistent cache: {cache_path}")

        except Exception as e:
            logger.warning(f"Failed to save persistent ROI cache: {e}")
