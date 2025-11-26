"""
ROI data service for fetching ROI information from Google Cloud Storage.

This service handles fetching ROI segment properties from GCS endpoints and
providing them as structured data for template rendering.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class ROIDataService:
    """
    Service for fetching and managing ROI data from Google Cloud Storage.

    This service handles:
    - Fetching ROI segment properties from GCS endpoints
    - Caching ROI data in output/.cache/roi_data/ to avoid repeated network requests
    - Parsing and structuring ROI data for template use
    - Error handling and retry logic for network requests
    """

    def __init__(self, output_dir: Optional[Path] = None, timeout: int = 30):
        """
        Initialize the ROI data service.

        Args:
            output_dir: Output directory containing the cache subdirectory (cache will be at output_dir/.cache/roi_data/)
            timeout: Timeout for HTTP requests in seconds
        """
        self.timeout = timeout
        if output_dir:
            self.cache_dir = Path(output_dir) / ".cache" / "roi_data"
        else:
            # Fallback to current working directory if no output_dir provided
            self.cache_dir = Path.cwd() / "output" / ".cache" / "roi_data"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # GCS endpoints for ROI data
        self.fullbrain_roi_url = "https://storage.googleapis.com/flyem-male-cns/rois/fullbrain-roi-v4/segment_properties/info"
        self.vnc_roi_url = "https://storage.googleapis.com/flyem-male-cns/rois/malecns-vnc-neuropil-roi-v0/segment_properties/info"

        # Cache for loaded data
        self._fullbrain_data = None
        self._vnc_data = None

    def _fetch_json_from_gcs(self, url: str, cache_filename: str) -> Dict[str, Any]:
        """
        Fetch JSON data from a GCS URL with caching.

        Args:
            url: GCS URL to fetch from
            cache_filename: Filename for local cache roi_data

        Returns:
            Parsed JSON data

        Raises:
            requests.RequestException: If the HTTP request fails
            json.JSONDecodeError: If the response is not valid JSON
        """
        cache_file = self.cache_dir / cache_filename

        # Try to load from cache first (cache for 1 hour)
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < 3600:  # 1 hour cache
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        logger.debug(f"Loaded ROI data from cache: {cache_filename}")
                        return data
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load cache file {cache_filename}: {e}")
                    # Delete corrupted cache file to force refetch
                    try:
                        cache_file.unlink()
                        logger.debug(f"Deleted corrupted cache file: {cache_filename}")
                    except OSError as unlink_error:
                        logger.warning(
                            f"Failed to delete corrupted cache file {cache_filename}: {unlink_error}"
                        )

        # Fetch from GCS
        logger.info(f"Fetching ROI data from: {url}")
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Validate that we have actual data before caching
            if not data or (isinstance(data, dict) and not any(data.values())):
                logger.warning(f"Received empty data from {url}, not caching")
                raise ValueError("Empty data received from GCS endpoint")

            # Cache the result
            try:
                with open(cache_file, "w") as f:
                    json.dump(data, f, indent=2)
                logger.debug(f"Cached ROI data to: {cache_filename}")
            except IOError as e:
                logger.warning(f"Failed to cache data to {cache_filename}: {e}")

            return data

        except requests.RequestException as e:
            logger.error(f"Failed to fetch ROI data from {url}: {e}")

            # Try to use stale cache as fallback
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        logger.warning(
                            f"Using stale cache for {cache_filename} due to fetch failure"
                        )
                        return data
                except (json.JSONDecodeError, IOError) as fallback_error:
                    logger.warning(
                        f"Stale cache file is also corrupted for {cache_filename}: {fallback_error}"
                    )
                    # Delete corrupted cache file
                    try:
                        cache_file.unlink()
                        logger.debug(
                            f"Deleted corrupted stale cache file: {cache_filename}"
                        )
                    except OSError as unlink_error:
                        logger.warning(
                            f"Failed to delete corrupted stale cache file {cache_filename}: {unlink_error}"
                        )

            raise

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from {url}: {e}")
            raise

    def _extract_roi_ids_and_names(
        self, segment_data: Dict[str, Any]
    ) -> Tuple[List[int], List[str]]:
        """
        Extract ROI IDs and names from Neuroglancer segment properties data.

        Args:
            segment_data: Raw segment properties data from GCS

        Returns:
            Tuple of (roi_ids, roi_names)
        """
        ids = []
        names = []

        # Handle Neuroglancer segment properties format
        if (
            "@type" in segment_data
            and segment_data["@type"] == "neuroglancer_segment_properties"
        ):
            inline_data = segment_data.get("inline", {})

            # Extract IDs
            segment_ids = inline_data.get("ids", [])

            # Extract names from properties
            properties = inline_data.get("properties", [])
            source_property = None

            # Find the "source" property that contains the labels
            for prop in properties:
                if prop.get("id") == "source" and prop.get("type") == "label":
                    source_property = prop
                    break

            if source_property and "values" in source_property:
                segment_names = source_property["values"]

                # Ensure we have the same number of IDs and names
                min_length = min(len(segment_ids), len(segment_names))

                for i in range(min_length):
                    try:
                        roi_id = int(segment_ids[i])
                        roi_name = str(segment_names[i])
                        ids.append(roi_id)
                        names.append(roi_name)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Could not parse ROI data at index {i}: {e}")

            # Sort by ID to ensure consistent ordering
            if ids and names:
                sorted_pairs = sorted(zip(ids, names), key=lambda x: x[0])
                ids, names = zip(*sorted_pairs)
                return list(ids), list(names)

        else:
            # Fallback to original parsing logic for other formats
            segments = segment_data.get("segments", [])

            for segment in segments:
                if isinstance(segment, dict):
                    segment_id = segment.get("id")
                    segment_name = segment.get(
                        "label", segment.get("name", f"ROI_{segment_id}")
                    )

                    if segment_id is not None:
                        ids.append(int(segment_id))
                        names.append(str(segment_name))
                elif isinstance(segment, (int, str)):
                    # Handle case where segments might be just IDs
                    try:
                        segment_id = int(segment)
                        ids.append(segment_id)
                        names.append(f"ROI_{segment_id}")
                    except ValueError:
                        logger.warning(f"Could not parse segment ID: {segment}")

            # Sort by ID to ensure consistent ordering
            if ids and names:
                sorted_pairs = sorted(zip(ids, names), key=lambda x: x[0])
                ids, names = zip(*sorted_pairs)
                return list(ids), list(names)

        return [], []

    def get_fullbrain_roi_data(self) -> Tuple[List[int], List[str]]:
        """
        Get fullbrain ROI IDs and names.

        Returns:
            Tuple of (roi_ids, roi_names)

        Raises:
            Exception: If fetching or parsing fails
        """
        if self._fullbrain_data is None:
            try:
                raw_data = self._fetch_json_from_gcs(
                    self.fullbrain_roi_url, "fullbrain_roi_v4.json"
                )
                self._fullbrain_data = self._extract_roi_ids_and_names(raw_data)
            except Exception as e:
                logger.error(f"Failed to get fullbrain ROI data: {e}")
                # Return empty data rather than crashing
                self._fullbrain_data = ([], [])

        return self._fullbrain_data

    def get_vnc_roi_data(self) -> Tuple[List[int], List[str]]:
        """
        Get VNC ROI IDs and names.

        Returns:
            Tuple of (roi_ids, roi_names)

        Raises:
            Exception: If fetching or parsing fails
        """
        if self._vnc_data is None:
            try:
                raw_data = self._fetch_json_from_gcs(
                    self.vnc_roi_url, "vnc_neuropil_roi_v0.json"
                )
                self._vnc_data = self._extract_roi_ids_and_names(raw_data)
            except Exception as e:
                logger.error(f"Failed to get VNC ROI data: {e}")
                # Return empty data rather than crashing
                self._vnc_data = ([], [])

        return self._vnc_data

    def get_all_roi_data(self) -> Dict[str, Any]:
        """
        Get all ROI data formatted for template use.

        Returns:
            Dictionary containing:
            - roi_ids: List of fullbrain ROI IDs
            - all_rois: List of fullbrain ROI names
            - vnc_ids: List of VNC ROI IDs
            - vnc_names: List of VNC ROI names
        """
        try:
            roi_ids, all_rois = self.get_fullbrain_roi_data()
            vnc_ids, vnc_names = self.get_vnc_roi_data()

            return {
                "roi_ids": roi_ids,
                "all_rois": all_rois,
                "vnc_ids": vnc_ids,
                "vnc_names": vnc_names,
            }
        except Exception as e:
            logger.error(f"Failed to get all ROI data: {e}")
            # Return empty data as fallback
            return {"roi_ids": [], "all_rois": [], "vnc_ids": [], "vnc_names": []}

    def refresh_cache(self) -> None:
        """
        Force refresh of cached ROI data by clearing cache and refetching.
        """
        logger.info("Refreshing ROI data cache")

        # Clear cached data
        self._fullbrain_data = None
        self._vnc_data = None

        # Remove cache files to force refetch
        cache_files = ["fullbrain_roi_v4.json", "vnc_neuropil_roi_v0.json"]
        for cache_file in cache_files:
            cache_path = self.cache_dir / cache_file
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    logger.debug(f"Removed cache file: {cache_file}")
                except OSError as e:
                    logger.warning(f"Failed to remove cache file {cache_file}: {e}")

        # Trigger refetch
        self.get_all_roi_data()

    def validate_roi_data(self) -> Dict[str, bool]:
        """
        Validate that ROI data is properly formatted and consistent.

        Returns:
            Dictionary with validation results
        """
        try:
            data = self.get_all_roi_data()

            results = {
                "has_fullbrain_data": len(data["roi_ids"]) > 0
                and len(data["all_rois"]) > 0,
                "has_vnc_data": len(data["vnc_ids"]) > 0 and len(data["vnc_names"]) > 0,
                "fullbrain_ids_names_match": len(data["roi_ids"])
                == len(data["all_rois"]),
                "vnc_ids_names_match": len(data["vnc_ids"]) == len(data["vnc_names"]),
                "no_duplicate_fullbrain_ids": len(data["roi_ids"])
                == len(set(data["roi_ids"])),
                "no_duplicate_vnc_ids": len(data["vnc_ids"])
                == len(set(data["vnc_ids"])),
            }

            # Log validation results
            for check, passed in results.items():
                if not passed:
                    logger.warning(f"ROI data validation failed: {check}")
                else:
                    logger.debug(f"ROI data validation passed: {check}")

            return results

        except Exception as e:
            logger.error(f"ROI data validation failed with exception: {e}")
            return {
                "has_fullbrain_data": False,
                "has_vnc_data": False,
                "fullbrain_ids_names_match": False,
                "vnc_ids_names_match": False,
                "no_duplicate_fullbrain_ids": False,
                "no_duplicate_vnc_ids": False,
            }
