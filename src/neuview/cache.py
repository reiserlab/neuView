"""
Persistent cache system for neuron type information.

This module provides caching functionality to store neuron type data during
page generation and reuse it during index creation, avoiding expensive
database re-queries.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class NeuronTypeCacheData:
    """Data structure for cached neuron type information."""

    neuron_type: str
    total_count: int
    soma_side_counts: Dict[str, int]
    synapse_stats: Dict[str, float]
    roi_summary: List[Dict[str, Any]]
    parent_rois: List[str]
    generation_timestamp: float
    soma_sides_available: List[str]
    has_connectivity: bool
    metadata: Dict[str, Any]
    consensus_nt: Optional[str] = None
    celltype_predicted_nt: Optional[str] = None
    celltype_predicted_nt_confidence: Optional[float] = None
    celltype_total_nt_predictions: Optional[int] = None
    cell_class: Optional[str] = None
    cell_subclass: Optional[str] = None
    cell_superclass: Optional[str] = None
    dimorphism: Optional[str] = None
    nt_analysis: Optional[List[Dict[str, Any]]] = None
    # Column data for optic lobe neurons
    columns_data: Optional[List[Dict[str, Any]]] = None
    region_columns_map: Optional[Dict[str, List[tuple]]] = None
    # Meta information to avoid queries during index creation
    original_neuron_name: Optional[str] = None
    synonyms: Optional[str] = None
    flywire_types: Optional[str] = None
    soma_neuromere: Optional[str] = None
    truman_hl: Optional[str] = None
    spatial_metrics: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None
    # Side-specific synapse counts
    side_synapse_stats: Optional[Dict[str, Dict[str, int]]] = None
    # Side-specific connection counts
    side_connection_stats: Optional[Dict[str, Dict[str, int]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        from typing import Any

        import numpy as np

        def convert_numpy_types(obj: Any) -> Any:
            """Convert numpy types to native Python types for JSON serialization."""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            return obj

        data = asdict(self)
        result = convert_numpy_types(data)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NeuronTypeCacheData":
        """Create instance from dictionary with required field validation."""
        # Validate required fields are present
        required_fields = {
            "neuron_type",
            "total_count",
            "soma_side_counts",
            "synapse_stats",
            "roi_summary",
            "parent_rois",
            "generation_timestamp",
            "soma_sides_available",
            "has_connectivity",
            "metadata",
        }

        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValueError(f"Missing required cache fields: {missing_fields}")

        return cls(**data)


class LazyCacheDataDict:
    """Dictionary-like object that loads cache data on-demand."""

    def __init__(self, cache_manager: "NeuronTypeCacheManager"):
        """Initialize with a cache manager."""
        self._cache_manager = cache_manager
        self._cache = {}  # In-memory cache of loaded data
        self._available_types = None  # Lazy-loaded list of available types

    def _get_available_types(self) -> List[str]:
        """Get list of available neuron types (cached)."""
        if self._available_types is None:
            self._available_types = self._cache_manager.list_cached_neuron_types()
        return self._available_types

    def get(self, neuron_type: str, default=None) -> Optional[NeuronTypeCacheData]:
        """Get cache data for a neuron type, loading if necessary."""
        if neuron_type in self._cache:
            return self._cache[neuron_type]

        # Load from disk
        cache_data = self._cache_manager.load_neuron_type_cache(neuron_type)
        if cache_data:
            self._cache[neuron_type] = cache_data
            return cache_data

        return default

    def __getitem__(self, neuron_type: str) -> NeuronTypeCacheData:
        """Get cache data for a neuron type, raising KeyError if not found."""
        result = self.get(neuron_type)
        if result is None:
            raise KeyError(f"No cache data found for neuron type: {neuron_type}")
        return result

    def __contains__(self, neuron_type: str) -> bool:
        """Check if neuron type has cache data available."""
        if neuron_type in self._cache:
            return True
        return self._cache_manager.has_cached_data(neuron_type)

    def keys(self):
        """Get iterator over available neuron type names."""
        return iter(self._get_available_types())

    def values(self):
        """Get iterator over all cache data values (loads all files)."""
        for neuron_type in self._get_available_types():
            yield self.get(neuron_type)

    def items(self):
        """Get iterator over (neuron_type, cache_data) pairs (loads all files)."""
        for neuron_type in self._get_available_types():
            cache_data = self.get(neuron_type)
            if cache_data:
                yield neuron_type, cache_data

    def __len__(self) -> int:
        """Get number of available neuron types."""
        return len(self._get_available_types())

    def __iter__(self):
        """Iterate over available neuron type names."""
        return iter(self._get_available_types())


class NeuronTypeCacheManager:
    """Manager for neuron type cache operations."""

    def __init__(self, cache_dir: str):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._roi_hierarchy_cache_path = self.cache_dir / "roi_hierarchy.json"
        logger.debug(f"Initialized cache manager with directory: {self.cache_dir}")

        # Cache expiry time (24 hours)
        self.cache_expiry_seconds = 24 * 3600

    def _get_cache_file_path(self, neuron_type: str) -> Path:
        """Get cache file path for a neuron type."""
        # Sanitize neuron type name for filename
        safe_name = "".join(c for c in neuron_type if c.isalnum() or c in "._-")
        return self.cache_dir / f"{safe_name}.json"

    def save_neuron_type_cache(self, cache_data: NeuronTypeCacheData) -> bool:
        """Save neuron type cache data to disk.

        Args:
            cache_data: Cache data to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            cache_file = self._get_cache_file_path(cache_data.neuron_type)

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data.to_dict(), f, indent=2, ensure_ascii=False)

            logger.debug(
                f"Saved cache for neuron type {cache_data.neuron_type} to {cache_file}"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to save cache for {cache_data.neuron_type}: {e}")
            return False

    def save_roi_hierarchy(self, hierarchy_data: dict) -> bool:
        """Save ROI hierarchy data to persistent cache.

        Args:
            hierarchy_data: ROI hierarchy dictionary

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            import time

            cache_data = {
                "hierarchy": hierarchy_data,
                "timestamp": time.time(),
                "cache_version": "1.0",
            }

            with open(self._roi_hierarchy_cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.debug(
                f"Saved ROI hierarchy to cache: {self._roi_hierarchy_cache_path}"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to save ROI hierarchy to cache: {e}")
            return False

    def load_roi_hierarchy(self) -> Optional[dict]:
        """Load ROI hierarchy data from persistent cache.

        Returns:
            ROI hierarchy dictionary if available and valid, None otherwise
        """
        try:
            if not self._roi_hierarchy_cache_path.exists():
                return None

            with open(self._roi_hierarchy_cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check cache validity (24 hours)
            if "timestamp" in cache_data:
                import time

                cache_age = time.time() - cache_data["timestamp"]
                if cache_age > self.cache_expiry_seconds:
                    logger.debug(f"ROI hierarchy cache expired (age: {cache_age:.1f}s)")
                    return None

            hierarchy = cache_data.get("hierarchy")
            if hierarchy:
                logger.debug(
                    f"Loaded ROI hierarchy from cache: {self._roi_hierarchy_cache_path}"
                )
                return hierarchy

        except Exception as e:
            logger.debug(f"Failed to load ROI hierarchy from cache: {e}")

        return None

    def load_neuron_type_cache(self, neuron_type: str) -> Optional[NeuronTypeCacheData]:
        """Load neuron type cache data from disk.

        Args:
            neuron_type: Name of neuron type to load

        Returns:
            Cache data if found and valid, None otherwise
        """
        try:
            cache_file = self._get_cache_file_path(neuron_type)

            if not cache_file.exists():
                return None

            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            cache_data = NeuronTypeCacheData.from_dict(data)

            # Check if cache is expired
            cache_age = time.time() - cache_data.generation_timestamp
            if cache_age > self.cache_expiry_seconds:
                logger.debug(
                    f"Cache for {neuron_type} is expired ({cache_age:.1f}s old)"
                )
                return None

            logger.debug(
                f"Loaded cache for neuron type {neuron_type} from {cache_file}"
            )
            return cache_data

        except Exception as e:
            logger.warning(f"Failed to load cache for {neuron_type}: {e}")
            return None

    def invalidate_neuron_type_cache(self, neuron_type: str) -> bool:
        """Remove cache file for a neuron type.

        Args:
            neuron_type: Name of neuron type to invalidate

        Returns:
            True if removed successfully, False otherwise
        """
        try:
            cache_file = self._get_cache_file_path(neuron_type)
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Invalidated cache for neuron type {neuron_type}")
                return True
            return False

        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {neuron_type}: {e}")
            return False

    def list_cached_neuron_types(self) -> List[str]:
        """Get list of neuron types that have valid cache files (lazy - no file loading).

        Returns:
            List of cached neuron type names
        """
        cached_types = []

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                # Skip ROI hierarchy cache file - it's not a neuron type cache
                if cache_file.name == "roi_hierarchy.json":
                    continue

                # Skip cache manifest file - it's not a neuron type cache
                if cache_file.name == "manifest.json":
                    continue

                # Skip auxiliary cache files (columns, etc.) - they're not neuron type caches
                if "_columns.json" in cache_file.name:
                    continue

                # Extract neuron type from filename and verify file is readable
                neuron_type = cache_file.stem
                if (
                    neuron_type
                    and cache_file.exists()
                    and cache_file.stat().st_size > 0
                ):
                    # Quick validation - check if it's a JSON file with basic structure
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            # Just peek at the first few chars to see if it looks like JSON
                            first_char = f.read(1)
                            if first_char == "{":
                                cached_types.append(neuron_type)
                    except Exception:
                        # Skip files that can't be read
                        pass

        except Exception as e:
            logger.warning(f"Failed to list cached neuron types: {e}")

        return sorted(cached_types)

    def get_all_cached_data(self) -> Dict[str, NeuronTypeCacheData]:
        """Get all valid cached neuron type data.

        WARNING: This method loads ALL cache files at once. Consider using
        get_cached_data_lazy() or load_neuron_type_cache() for individual types.

        Returns:
            Dictionary mapping neuron type names to cache data
        """
        cached_data = {}

        for neuron_type in self.list_cached_neuron_types():
            cache_data = self.load_neuron_type_cache(neuron_type)
            if cache_data:
                cached_data[neuron_type] = cache_data

        return cached_data

    def get_cached_data_lazy(self) -> "LazyCacheDataDict":
        """Get a lazy-loading dictionary for cached neuron type data.

        Returns a dictionary-like object that only loads cache files when accessed.

        Returns:
            LazyCacheDataDict that loads data on-demand
        """
        return LazyCacheDataDict(self)

    def has_cached_data(self, neuron_type: str) -> bool:
        """Check if cache data exists for a neuron type without loading it.

        Args:
            neuron_type: Name of neuron type to check

        Returns:
            True if cache file exists, False otherwise
        """
        cache_file = self._get_cache_file_path(neuron_type)
        return cache_file.exists()


def create_cache_manager(output_dir: str) -> NeuronTypeCacheManager:
    """Create a cache manager for the given output directory.

    Args:
        output_dir: Output directory where cache should be stored

    Returns:
        Configured cache manager instance
    """
    cache_dir = Path(output_dir) / ".cache"
    return NeuronTypeCacheManager(str(cache_dir))
