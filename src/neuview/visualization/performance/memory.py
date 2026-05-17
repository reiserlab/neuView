"""
Memory optimization utilities for eyemap visualization.

This module provides memory-efficient processing strategies for large
hexagon collections and other memory-intensive operations in eyemap generation.
"""

import gc
import logging

import psutil

from collections import deque
from contextlib import contextmanager
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class MemoryOptimizer:
    """
    Memory optimization utilities for eyemap processing.

    Provides memory monitoring, optimization strategies, and
    memory-efficient processing patterns for large datasets.
    """

    def __init__(self, memory_threshold_mb: int = None):
        """
        Initialize memory optimizer.

        Args:
            memory_threshold_mb: Memory threshold in MB for optimization triggers.
                                If None, uses configured default.
        """
        # Use configurable thresholds
        from ...services.threshold_service import ThresholdService

        self._threshold_service = ThresholdService()
        thresholds = self._threshold_service.get_memory_thresholds()

        self.memory_threshold_mb = (
            memory_threshold_mb
            if memory_threshold_mb is not None
            else thresholds["optimization_trigger"]
        )
        self.process = psutil.Process()

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def get_memory_percent(self) -> float:
        """Get current memory usage as percentage of system memory."""
        return self.process.memory_percent()

    def is_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        return self.get_memory_usage_mb() > self.memory_threshold_mb

    def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return statistics."""
        before_objects = len(gc.get_objects())
        before_memory = self.get_memory_usage_mb()

        # Force collection of all generations
        collected = [gc.collect(generation) for generation in range(3)]

        after_objects = len(gc.get_objects())
        after_memory = self.get_memory_usage_mb()

        return {
            "objects_before": before_objects,
            "objects_after": after_objects,
            "objects_freed": before_objects - after_objects,
            "memory_before_mb": before_memory,
            "memory_after_mb": after_memory,
            "memory_freed_mb": before_memory - after_memory,
            "collected_by_generation": collected,
        }

    def optimize_if_needed(self) -> Optional[Dict[str, int]]:
        """Run optimization if memory pressure is detected."""
        if self.is_memory_pressure():
            logger.warning(
                f"Memory pressure detected: {self.get_memory_usage_mb():.1f}MB"
            )
            return self.force_garbage_collection()
        return None

    @contextmanager
    def memory_monitoring(self, operation_name: str = "operation"):
        """Context manager for monitoring memory usage during operations."""
        start_memory = self.get_memory_usage_mb()
        start_objects = len(gc.get_objects())

        logger.debug(
            f"Starting {operation_name} - Memory: {start_memory:.1f}MB, Objects: {start_objects}"
        )

        try:
            yield self
        finally:
            end_memory = self.get_memory_usage_mb()
            end_objects = len(gc.get_objects())

            memory_delta = end_memory - start_memory
            objects_delta = end_objects - start_objects

            logger.debug(
                f"Completed {operation_name} - "
                f"Memory: {end_memory:.1f}MB ({memory_delta:+.1f}MB), "
                f"Objects: {end_objects} ({objects_delta:+d})"
            )

            # Auto-optimize if significant memory increase
            if memory_delta > 100:  # 100MB increase
                self.optimize_if_needed()


class StreamingHexagonProcessor:
    """
    Memory-efficient processor for large hexagon collections.

    Processes hexagons in batches to minimize memory usage and
    provides streaming interfaces for large datasets.
    """

    def __init__(
        self, batch_size: int = 1000, memory_optimizer: Optional[MemoryOptimizer] = None
    ):
        """
        Initialize streaming processor.

        Args:
            batch_size: Number of hexagons to process in each batch
            memory_optimizer: Memory optimizer instance for monitoring
        """
        self.batch_size = batch_size
        self.memory_optimizer = memory_optimizer or MemoryOptimizer()

    def process_hexagons_streaming(
        self, hexagon_generator: Iterator[Dict], processor_func: callable
    ) -> Generator[List[Dict], None, None]:
        """
        Process hexagons in memory-efficient streaming batches.

        Args:
            hexagon_generator: Generator yielding hexagon dictionaries
            processor_func: Function to process each batch of hexagons

        Yields:
            Processed hexagon batches
        """
        batch = []
        batch_count = 0

        for hexagon in hexagon_generator:
            batch.append(hexagon)

            if len(batch) >= self.batch_size:
                # Process batch
                with self.memory_optimizer.memory_monitoring(f"batch_{batch_count}"):
                    processed_batch = processor_func(batch)
                    yield processed_batch

                # Clear batch and optionally run GC
                batch.clear()
                batch_count += 1

                if batch_count % 10 == 0:  # Every 10 batches
                    self.memory_optimizer.optimize_if_needed()

        # Process remaining hexagons
        if batch:
            with self.memory_optimizer.memory_monitoring("final_batch"):
                processed_batch = processor_func(batch)
                yield processed_batch

    def create_hexagon_iterator(self, hexagon_data: List[Dict]) -> Iterator[Dict]:
        """Create memory-efficient iterator for hexagon data."""
        for hexagon in hexagon_data:
            yield hexagon

    def batch_coordinate_conversion(
        self, columns: List[Dict], coordinate_converter: callable
    ) -> Generator[Dict[Tuple, Dict], None, None]:
        """
        Convert coordinates in memory-efficient batches.

        Args:
            columns: List of column dictionaries
            coordinate_converter: Function to convert coordinates

        Yields:
            Coordinate mapping dictionaries for each batch
        """

        def process_batch(batch_columns):
            return coordinate_converter(batch_columns)

        # Create iterator and process in batches
        column_iterator = iter(columns)

        while True:
            batch = list(self._take(column_iterator, self.batch_size))
            if not batch:
                break

            with self.memory_optimizer.memory_monitoring("coordinate_batch"):
                yield process_batch(batch)

    def batch_color_computation(
        self, processed_columns: Iterator, color_computer: callable
    ) -> Generator[List[str], None, None]:
        """
        Compute colors in memory-efficient batches.

        Args:
            processed_columns: Iterator of processed column data
            color_computer: Function to compute colors

        Yields:
            Lists of computed colors for each batch
        """

        def process_batch(batch_columns):
            return [color_computer(col) for col in batch_columns]

        batch = []
        for column in processed_columns:
            batch.append(column)

            if len(batch) >= self.batch_size:
                with self.memory_optimizer.memory_monitoring("color_batch"):
                    yield process_batch(batch)
                batch.clear()
                self.memory_optimizer.optimize_if_needed()

        # Process remaining
        if batch:
            with self.memory_optimizer.memory_monitoring("final_color_batch"):
                yield process_batch(batch)

    def _take(self, iterator: Iterator, n: int) -> Iterator:
        """Take n items from iterator."""
        for _ in range(n):
            try:
                yield next(iterator)
            except StopIteration:
                break


class LazyHexagonCollection:
    """
    Lazy-loaded collection for large hexagon datasets.

    Provides dict-like interface while loading data on-demand
    to minimize memory usage.
    """

    def __init__(self, data_source: Union[List[Dict], callable], chunk_size: int = 500):
        """
        Initialize lazy collection.

        Args:
            data_source: List of data or callable that returns data
            chunk_size: Size of data chunks to load at once
        """
        self.data_source = data_source
        self.chunk_size = chunk_size
        self._cache = {}
        self._loaded_chunks = set()
        self._chunk_access_order = deque()  # Track access order for LRU
        self._total_size = None

    def __len__(self) -> int:
        """Get total size of collection."""
        if self._total_size is None:
            if callable(self.data_source):
                # For callable sources, we need to estimate or load metadata
                self._total_size = self._get_source_size()
            else:
                self._total_size = len(self.data_source)
        return self._total_size

    def __getitem__(self, key: Union[int, slice]) -> Union[Dict, List[Dict]]:
        """Get item(s) by index."""
        if isinstance(key, slice):
            return self._get_slice(key)
        else:
            return self._get_item(key)

    def __iter__(self) -> Iterator[Dict]:
        """Iterate over all items."""
        for i in range(len(self)):
            yield self[i]

    def _get_item(self, index: int) -> Dict:
        """Get single item by index."""
        chunk_id = index // self.chunk_size

        if chunk_id not in self._loaded_chunks:
            self._load_chunk(chunk_id)
        else:
            # Update access order for already loaded chunk
            if chunk_id in self._chunk_access_order:
                self._chunk_access_order.remove(chunk_id)
            self._chunk_access_order.append(chunk_id)

        return self._cache[index]

    def _get_slice(self, slice_obj: slice) -> List[Dict]:
        """Get slice of items."""
        start, stop, step = slice_obj.indices(len(self))
        return [self[i] for i in range(start, stop, step or 1)]

    def _load_chunk(self, chunk_id: int) -> None:
        """Load specific chunk of data."""
        start_idx = chunk_id * self.chunk_size
        end_idx = min(start_idx + self.chunk_size, len(self))

        if callable(self.data_source):
            chunk_data = self.data_source(start_idx, end_idx)
        else:
            chunk_data = self.data_source[start_idx:end_idx]

        # Cache the chunk
        for i, item in enumerate(chunk_data):
            self._cache[start_idx + i] = item

        self._loaded_chunks.add(chunk_id)

        # Track access order for LRU
        if chunk_id in self._chunk_access_order:
            self._chunk_access_order.remove(chunk_id)
        self._chunk_access_order.append(chunk_id)

        # Memory management: unload old chunks if too many loaded
        if len(self._loaded_chunks) > 5:  # Keep max 5 chunks for better memory usage
            self._unload_lru_chunks()

    def _unload_lru_chunks(self) -> None:
        """Unload least recently used chunks to free memory."""
        max_chunks = 3  # Keep only the 3 most recently accessed chunks

        while len(self._loaded_chunks) > max_chunks and self._chunk_access_order:
            # Remove least recently used chunk (first in deque)
            lru_chunk_id = self._chunk_access_order.popleft()

            if lru_chunk_id in self._loaded_chunks:
                self._unload_chunk(lru_chunk_id)

    def _unload_chunk(self, chunk_id: int) -> None:
        """Unload a specific chunk from memory."""
        start_idx = chunk_id * self.chunk_size
        end_idx = min(start_idx + self.chunk_size, len(self))

        # Remove from cache
        for idx in range(start_idx, end_idx):
            self._cache.pop(idx, None)

        self._loaded_chunks.discard(chunk_id)

    def _get_source_size(self) -> int:
        """Get size from callable data source with improved estimation."""
        if hasattr(self.data_source, "__len__"):
            return len(self.data_source)
        elif hasattr(self.data_source, "get_size"):
            return self.data_source.get_size()
        else:
            # Progressive estimation strategy
            first_chunk = self.data_source(0, self.chunk_size)
            first_chunk_size = len(first_chunk)

            # If first chunk is smaller than chunk_size, we have the complete dataset
            if first_chunk_size < self.chunk_size:
                return first_chunk_size

            # Try a second chunk to get a better estimate
            try:
                second_chunk = self.data_source(self.chunk_size, 2 * self.chunk_size)
                second_chunk_size = len(second_chunk)

                if second_chunk_size < self.chunk_size:
                    # Second chunk is partial, so total is first chunk + second chunk
                    return first_chunk_size + second_chunk_size
                else:
                    # Both chunks are full, estimate based on average chunk density
                    # Use conservative estimate: assume at least 5 chunks, but not more than 20
                    avg_chunk_size = (first_chunk_size + second_chunk_size) / 2
                    estimated_chunks = max(
                        5, min(20, int(10 * avg_chunk_size / self.chunk_size))
                    )
                    return int(avg_chunk_size * estimated_chunks)
            except (IndexError, AttributeError):
                # Fallback to single chunk estimation
                return first_chunk_size * 5  # Conservative estimate


def memory_efficient_processing(
    data: Union[List, Iterator],
    processor: callable,
    batch_size: int = 1000,
    memory_threshold_mb: int = None,
) -> Generator[Any, None, None]:
    """
    Process data in memory-efficient batches.

    Args:
        data: Input data to process
        processor: Function to process each batch
        batch_size: Size of processing batches
        memory_threshold_mb: Memory threshold for optimization. If None, uses configured default.

    Yields:
        Processed results
    """
    # Use configurable threshold if not specified
    if memory_threshold_mb is None:
        from ...services.threshold_service import ThresholdService

        threshold_service = ThresholdService()
        thresholds = threshold_service.get_memory_thresholds()
        memory_threshold_mb = thresholds["optimization_trigger"]
    optimizer = MemoryOptimizer(memory_threshold_mb)

    if isinstance(data, list):
        data_iter = iter(data)
    else:
        data_iter = data

    batch = []
    batch_count = 0

    for item in data_iter:
        batch.append(item)

        if len(batch) >= batch_size:
            with optimizer.memory_monitoring(f"batch_{batch_count}"):
                result = processor(batch)
                yield result

            batch.clear()
            batch_count += 1

            if batch_count % 5 == 0:
                optimizer.optimize_if_needed()

    # Process final batch
    if batch:
        with optimizer.memory_monitoring("final_batch"):
            result = processor(batch)
            yield result


@contextmanager
def memory_limit_context(limit_mb: int):
    """
    Context manager to enforce memory limits during processing.

    Args:
        limit_mb: Memory limit in megabytes
    """
    optimizer = MemoryOptimizer(limit_mb)

    try:
        yield optimizer
    finally:
        final_memory = optimizer.get_memory_usage_mb()
        if final_memory > limit_mb:
            logger.warning(
                f"Memory limit exceeded: {final_memory:.1f}MB > {limit_mb}MB"
            )
            optimizer.force_garbage_collection()


