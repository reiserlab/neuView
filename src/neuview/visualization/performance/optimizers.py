"""
Specialized optimizer classes for different eyemap operations.

This module provides optimized implementations for specific eyemap operations
like coordinate calculations, color computations, metadata generation, and
hexagon collection processing with caching and performance enhancements.
"""

import hashlib
import logging
from abc import ABC
from typing import Dict, List, Optional, Tuple

from .cache import get_cache_manager
from .memory import MemoryOptimizer, StreamingHexagonProcessor
from .monitoring import performance_timer

logger = logging.getLogger(__name__)


class BaseOptimizer(ABC):
    """
    Base class for all eyemap optimizers.

    Provides common functionality for caching, monitoring, and memory management.
    """

    def __init__(self, cache_enabled: bool = True, monitoring_enabled: bool = True):
        """
        Initialize base optimizer.

        Args:
            cache_enabled: Whether to enable caching for this optimizer
            monitoring_enabled: Whether to enable performance monitoring
        """
        self.cache_enabled = cache_enabled
        self.monitoring_enabled = monitoring_enabled
        self.memory_optimizer = MemoryOptimizer()
        self.cache_manager = get_cache_manager()

    def _should_use_cache(self) -> bool:
        """Check if caching should be used."""
        return self.cache_enabled and self.cache_manager is not None

    def _generate_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()


class CoordinateOptimizer(BaseOptimizer):
    """
    Optimized coordinate conversion with intelligent caching.

    Features:
    - Coordinate transformation caching
    - Batch processing for large datasets
    - Memory-efficient processing
    - Smart cache key generation based on coordinate patterns
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._coordinate_cache = (
            self.cache_manager.get_cache("coordinates")
            if self._should_use_cache()
            else None
        )

    @performance_timer("coordinate_conversion")

    def _generate_coordinate_cache_key(
        self, columns: List[Dict], soma_side: Optional[str]
    ) -> str:
        """Generate optimized cache key for coordinate data."""
        # Create key based on column range and soma side rather than full data
        if not columns:
            return "empty"

        hex1_values = [col.get("hex1", 0) for col in columns]
        hex2_values = [col.get("hex2", 0) for col in columns]

        key_components = [
            f"hex1_range:{min(hex1_values)}_{max(hex1_values)}",
            f"hex2_range:{min(hex2_values)}_{max(hex2_values)}",
            f"count:{len(columns)}",
            f"soma_side:{soma_side or 'none'}",
        ]

        return hashlib.md5("_".join(key_components).encode()).hexdigest()

    def _direct_coordinate_conversion(
        self, columns: List[Dict], soma_side: Optional[str], coordinate_system
    ) -> Dict:
        """Direct coordinate conversion for smaller datasets."""
        columns_with_coords = coordinate_system.convert_column_coordinates(
            columns, mirror_side=soma_side
        )

        return {
            (col["hex1"], col["hex2"]): {"x": col["x"], "y": col["y"]}
            for col in columns_with_coords
        }

    def _batch_coordinate_conversion(
        self, columns: List[Dict], soma_side: Optional[str], coordinate_system
    ) -> Dict:
        """Memory-efficient batch coordinate conversion for large datasets."""
        streaming_processor = StreamingHexagonProcessor(batch_size=1000)
        result = {}

        def process_batch(batch_columns):
            batch_coords = coordinate_system.convert_column_coordinates(
                batch_columns, mirror_side=soma_side
            )
            return {
                (col["hex1"], col["hex2"]): {"x": col["x"], "y": col["y"]}
                for col in batch_coords
            }

        # Process in batches and merge results
        for batch_result in streaming_processor.batch_coordinate_conversion(
            columns, process_batch
        ):
            result.update(batch_result)

        return result


class ColorOptimizer(BaseOptimizer):
    """
    Optimized color computation with value-based caching.

    Features:
    - Color calculation caching based on value ranges
    - Batch color computation
    - Memory-efficient color mapping
    - Smart cache invalidation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._color_cache = (
            self.cache_manager.get_cache("colors") if self._should_use_cache() else None
        )

    @performance_timer("color_computation")
    def compute_color_optimized(
        self,
        processed_col,
        min_value: float,
        max_value: float,
        color_mapper,
        color_palette,
    ) -> Optional[str]:
        """
        Optimized color computation with caching.

        Args:
            processed_col: Processed column data with status and value
            min_value: Minimum value for color mapping range
            max_value: Maximum value for color mapping range
            color_mapper: Color mapper instance
            color_palette: Color palette instance

        Returns:
            Color string (hex code) or None if hexagon should be skipped
        """
        # For static colors (status-based), return immediately
        if hasattr(processed_col, "status"):
            from ..data_processing.data_structures import ColumnStatus

            if processed_col.status == ColumnStatus.NO_DATA:
                return color_palette.white
            elif processed_col.status == ColumnStatus.NOT_IN_REGION:
                return color_palette.dark_gray
            elif processed_col.status != ColumnStatus.HAS_DATA:
                return None

        # For value-based colors, use caching
        if not hasattr(processed_col, "value"):
            return None

        value = processed_col.value
        cache_key = self._generate_color_cache_key(value, min_value, max_value)

        if self._color_cache:
            cached_color = self._color_cache.get(cache_key)
            if cached_color is not None:
                return cached_color

        # Compute color
        color = color_mapper.map_value_to_color(value, min_value, max_value)

        # Cache the result
        if self._color_cache and color is not None:
            self._color_cache.put(cache_key, color)

        return color


    def _generate_color_cache_key(
        self, value: float, min_value: float, max_value: float
    ) -> str:
        """Generate cache key for color computation."""
        # Quantize value to reduce cache key space while maintaining accuracy
        value_range = max_value - min_value
        if value_range > 0:
            normalized_value = (value - min_value) / value_range
            quantized_value = round(normalized_value * 1000) / 1000  # 3 decimal places
        else:
            quantized_value = 0.0

        return f"color_{quantized_value}_{min_value}_{max_value}"


class MetadataOptimizer(BaseOptimizer):
    """
    Optimized metadata generation with template-based caching.

    Features:
    - Metadata template caching
    - String interpolation optimization
    - Batch metadata generation
    - Smart cache key generation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._metadata_cache = (
            self.cache_manager.get_cache("metadata")
            if self._should_use_cache()
            else None
        )

    @performance_timer("metadata_generation")

    def _generate_metadata_cache_key(self, request) -> str:
        """Generate cache key for metadata based on request parameters."""
        key_components = [
            f"region:{request.region_name}",
            f"neuron:{request.neuron_type}",
            f"metric:{request.metric_type}",
            f"soma:{request.soma_side or 'none'}",
        ]
        return "_".join(key_components)

    def _generate_metadata(
        self, request, value_range: Dict[str, float]
    ) -> Dict[str, str]:
        """Generate metadata with optimized string formatting."""
        from ..constants import METRIC_SYNAPSE_DENSITY

        # Pre-format soma side to avoid repeated processing
        # Handle both string and SomaSide enum inputs
        if hasattr(request.soma_side, "value"):
            soma_display = (
                request.soma_side.value.upper()[:1] if request.soma_side else ""
            )
        else:
            soma_display = (
                str(request.soma_side).upper()[:1] if request.soma_side else ""
            )

        if request.metric_type == METRIC_SYNAPSE_DENSITY:
            title = f"{request.region_name} Synapses (All Columns)"
            subtitle = f"{request.neuron_type} ({soma_display})"
        else:  # cell_count
            title = f"{request.region_name} Cell Count (All Columns)"
            subtitle = f"{request.neuron_type} ({soma_display})"

        return {"title": title, "subtitle": subtitle}


class HexagonCollectionOptimizer(BaseOptimizer):
    """
    Optimized hexagon collection processing with streaming and batching.

    Features:
    - Memory-efficient hexagon processing
    - Streaming hexagon creation
    - Progressive rendering support
    """

    def __init__(self, batch_size: int = 1000, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.streaming_processor = StreamingHexagonProcessor(
            batch_size=batch_size, memory_optimizer=self.memory_optimizer
        )

    @performance_timer("hexagon_collection_creation")

    def _create_hexagons_streaming(
        self, processing_result, coord_to_pixel, request, value_range, color_optimizer
    ):
        """Create hexagons using streaming processing for large datasets."""
        hexagons = []

        def process_hexagon_batch(batch_columns):
            batch_hexagons = []
            for processed_col in batch_columns:
                hexagon = self._create_single_hexagon(
                    processed_col, coord_to_pixel, request, value_range, color_optimizer
                )
                if hexagon:
                    batch_hexagons.append(hexagon)
            return batch_hexagons

        # Process in streaming batches
        column_iterator = iter(processing_result.processed_columns)
        for batch_hexagons in self.streaming_processor.process_hexagons_streaming(
            column_iterator, process_hexagon_batch
        ):
            hexagons.extend(batch_hexagons)

        return hexagons

    def _create_hexagons_direct(
        self, processing_result, coord_to_pixel, request, value_range, color_optimizer
    ):
        """Create hexagons using direct processing for smaller datasets."""
        hexagons = []

        with self.memory_optimizer.memory_monitoring("direct_hexagon_creation"):
            for processed_col in processing_result.processed_columns:
                hexagon = self._create_single_hexagon(
                    processed_col, coord_to_pixel, request, value_range, color_optimizer
                )
                if hexagon:
                    hexagons.append(hexagon)

        return hexagons

    def _create_single_hexagon(
        self, processed_col, coord_to_pixel, request, value_range, color_optimizer
    ):
        """Create a single hexagon with optimized processing."""
        hex1, hex2 = processed_col.hex1, processed_col.hex2
        coord_key = (hex1, hex2)

        if coord_key not in coord_to_pixel:
            return None

        pixel_coords = coord_to_pixel[coord_key]

        # Use optimized color computation
        color = color_optimizer.compute_color_optimized(
            processed_col,
            value_range["min_value"],
            value_range["max_value"],
            None,  # These would be passed from the calling context
            None,  # These would be passed from the calling context
        )

        if color is None:
            return None

        return {
            "x": pixel_coords["x"],
            "y": pixel_coords["y"],
            "hex1": hex1,
            "hex2": hex2,
            "color": color,
            "value": getattr(processed_col, "value", 0),
            "status": getattr(processed_col, "status", "unknown"),
            "region": request.region_name,
            "layer_values": getattr(processed_col, "layer_values", []),
        }


class PerformanceOptimizerFactory:
    """Factory for creating optimized instances with shared configuration."""

    @staticmethod
    def create_coordinate_optimizer(
        cache_enabled: bool = True, monitoring_enabled: bool = True
    ) -> CoordinateOptimizer:
        """Create coordinate optimizer with configuration."""
        return CoordinateOptimizer(
            cache_enabled=cache_enabled, monitoring_enabled=monitoring_enabled
        )

    @staticmethod
    def create_color_optimizer(
        cache_enabled: bool = True, monitoring_enabled: bool = True
    ) -> ColorOptimizer:
        """Create color optimizer with configuration."""
        return ColorOptimizer(
            cache_enabled=cache_enabled, monitoring_enabled=monitoring_enabled
        )

    @staticmethod
    def create_metadata_optimizer(
        cache_enabled: bool = True, monitoring_enabled: bool = True
    ) -> MetadataOptimizer:
        """Create metadata optimizer with configuration."""
        return MetadataOptimizer(
            cache_enabled=cache_enabled, monitoring_enabled=monitoring_enabled
        )

    @staticmethod
    def create_hexagon_optimizer(
        batch_size: int = 1000,
        cache_enabled: bool = True,
        monitoring_enabled: bool = True,
    ) -> HexagonCollectionOptimizer:
        """Create hexagon collection optimizer with configuration."""
        return HexagonCollectionOptimizer(
            batch_size=batch_size,
            cache_enabled=cache_enabled,
            monitoring_enabled=monitoring_enabled,
        )

    @staticmethod
    def create_full_optimizer_suite() -> Dict[str, BaseOptimizer]:
        """Create complete suite of optimizers."""
        return {
            "coordinate": PerformanceOptimizerFactory.create_coordinate_optimizer(),
            "color": PerformanceOptimizerFactory.create_color_optimizer(),
            "metadata": PerformanceOptimizerFactory.create_metadata_optimizer(),
            "hexagon": PerformanceOptimizerFactory.create_hexagon_optimizer(),
        }
