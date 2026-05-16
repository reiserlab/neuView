"""
Performance monitoring system for eyemap visualization operations.

This module provides comprehensive performance monitoring, timing, and
metrics collection for eyemap generation operations to identify
bottlenecks and optimize performance.
"""

import logging
import time
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Container for a single performance metric."""

    name: str
    duration: float
    timestamp: float
    memory_before: float
    memory_after: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def memory_delta(self) -> float:
        """Memory change during operation."""
        return self.memory_after - self.memory_before

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "duration_ms": self.duration * 1000,
            "timestamp": self.timestamp,
            "memory_before_mb": self.memory_before,
            "memory_after_mb": self.memory_after,
            "memory_delta_mb": self.memory_delta,
            "metadata": self.metadata,
        }


@dataclass
class OperationStats:
    """Statistics for a specific operation type."""

    operation_name: str
    call_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float("inf")
    max_duration: float = 0.0
    avg_memory_delta: float = 0.0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_duration(self) -> float:
        """Average duration across all calls."""
        return self.total_duration / self.call_count if self.call_count > 0 else 0.0

    @property
    def recent_avg_duration(self) -> float:
        """Average duration of recent calls."""
        return (
            sum(self.recent_durations) / len(self.recent_durations)
            if self.recent_durations
            else 0.0
        )

    def add_metric(self, metric: PerformanceMetric) -> None:
        """Add a new metric to the statistics."""
        self.call_count += 1
        self.total_duration += metric.duration
        self.min_duration = min(self.min_duration, metric.duration)
        self.max_duration = max(self.max_duration, metric.duration)
        self.recent_durations.append(metric.duration)

        # Update average memory delta
        total_memory_delta = (
            self.avg_memory_delta * (self.call_count - 1)
        ) + metric.memory_delta
        self.avg_memory_delta = total_memory_delta / self.call_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "operation_name": self.operation_name,
            "call_count": self.call_count,
            "total_duration_ms": self.total_duration * 1000,
            "avg_duration_ms": self.avg_duration * 1000,
            "recent_avg_duration_ms": self.recent_avg_duration * 1000,
            "min_duration_ms": self.min_duration * 1000
            if self.min_duration != float("inf")
            else 0,
            "max_duration_ms": self.max_duration * 1000,
            "avg_memory_delta_mb": self.avg_memory_delta,
        }


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for eyemap operations.

    Features:
    - Operation timing and profiling
    - Memory usage tracking
    - Cache performance metrics
    - Bottleneck identification
    - Performance trend analysis
    """

    def __init__(self, max_metrics: int = 10000):
        """
        Initialize performance monitor.

        Args:
            max_metrics: Maximum number of metrics to store in memory
        """
        self.max_metrics = max_metrics
        self._metrics = deque(maxlen=max_metrics)
        self._operation_stats = defaultdict(lambda: OperationStats("unknown"))
        self._lock = threading.Lock()
        self._process = psutil.Process()

        # Performance thresholds (in seconds) - now configurable
        from ...services.threshold_service import ThresholdService

        self._threshold_service = ThresholdService()
        thresholds = self._threshold_service.get_performance_thresholds()
        self.slow_operation_threshold = thresholds["slow_operation"]
        self.very_slow_operation_threshold = thresholds["very_slow_operation"]

    def record_metric(
        self,
        name: str,
        duration: float,
        memory_before: float,
        memory_after: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a performance metric.

        Args:
            name: Operation name
            duration: Operation duration in seconds
            memory_before: Memory usage before operation (MB)
            memory_after: Memory usage after operation (MB)
            metadata: Additional metadata about the operation
        """
        metric = PerformanceMetric(
            name=name,
            duration=duration,
            timestamp=time.time(),
            memory_before=memory_before,
            memory_after=memory_after,
            metadata=metadata or {},
        )

        with self._lock:
            self._metrics.append(metric)
            self._operation_stats[name].operation_name = name
            self._operation_stats[name].add_metric(metric)

        # Log slow operations
        if duration > self.very_slow_operation_threshold:
            logger.warning(f"Very slow operation detected: {name} took {duration:.2f}s")
        elif duration > self.slow_operation_threshold:
            logger.info(f"Slow operation detected: {name} took {duration:.2f}s")

    def get_current_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        return self._process.memory_info().rss / 1024 / 1024

    def get_operation_stats(
        self, operation_name: Optional[str] = None
    ) -> Union[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Get statistics for operations.

        Args:
            operation_name: Specific operation name, or None for all operations

        Returns:
            Statistics dictionary for the operation, or all operations
        """
        with self._lock:
            if operation_name:
                if operation_name in self._operation_stats:
                    return self._operation_stats[operation_name].to_dict()
                else:
                    return {}
            else:
                return {
                    name: stats.to_dict()
                    for name, stats in self._operation_stats.items()
                }

    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent performance metrics."""
        with self._lock:
            recent = list(self._metrics)[-limit:]
            return [metric.to_dict() for metric in recent]

    def get_slowest_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the slowest recorded operations."""
        with self._lock:
            sorted_metrics = sorted(
                self._metrics, key=lambda m: m.duration, reverse=True
            )
            return [metric.to_dict() for metric in sorted_metrics[:limit]]

    def get_memory_intensive_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get operations with highest memory usage."""
        with self._lock:
            sorted_metrics = sorted(
                self._metrics, key=lambda m: abs(m.memory_delta), reverse=True
            )
            return [metric.to_dict() for metric in sorted_metrics[:limit]]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        with self._lock:
            total_operations = len(self._metrics)
            if total_operations == 0:
                return {"total_operations": 0, "message": "No operations recorded"}

            # Calculate overall statistics
            total_duration = sum(m.duration for m in self._metrics)
            avg_duration = total_duration / total_operations

            memory_deltas = [m.memory_delta for m in self._metrics]
            avg_memory_delta = sum(memory_deltas) / len(memory_deltas)

            slow_operations = sum(
                1 for m in self._metrics if m.duration > self.slow_operation_threshold
            )
            very_slow_operations = sum(
                1
                for m in self._metrics
                if m.duration > self.very_slow_operation_threshold
            )

            return {
                "total_operations": total_operations,
                "total_duration_ms": total_duration * 1000,
                "avg_duration_ms": avg_duration * 1000,
                "avg_memory_delta_mb": avg_memory_delta,
                "slow_operations": slow_operations,
                "very_slow_operations": very_slow_operations,
                "slow_operation_percentage": (slow_operations / total_operations) * 100,
                "current_memory_mb": self.get_current_memory_mb(),
                "unique_operations": len(self._operation_stats),
                "most_frequent_operation": max(
                    self._operation_stats.keys(),
                    key=lambda k: self._operation_stats[k].call_count,
                )
                if self._operation_stats
                else None,
            }

    def clear_metrics(self) -> None:
        """Clear all recorded metrics."""
        with self._lock:
            self._metrics.clear()
            self._operation_stats.clear()

    def set_thresholds(self, slow: float = None, very_slow: float = None) -> None:
        """
        Set performance thresholds. If values are None, uses configured defaults.

        Args:
            slow: Threshold for slow operations (seconds), None to use config
            very_slow: Threshold for very slow operations (seconds), None to use config
        """
        if slow is not None:
            self.slow_operation_threshold = slow
            # Update configuration
            self._threshold_service.config.set_threshold_value(
                "performance_slow_operation", slow
            )

        if very_slow is not None:
            self.very_slow_operation_threshold = very_slow
            # Update configuration
            self._threshold_service.config.set_threshold_value(
                "performance_very_slow_operation", very_slow
            )


def performance_timer(
    operation_name: Optional[str] = None,
    include_memory: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Decorator for timing function execution and recording performance metrics.

    Args:
        operation_name: Name for the operation (defaults to function name)
        include_memory: Whether to track memory usage
        metadata: Additional metadata to include with the metric
    """

    def decorator(func: Callable) -> Callable:
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()

            # Get initial state
            start_time = time.time()
            memory_before = monitor.get_current_memory_mb() if include_memory else 0.0

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Record performance metrics
                end_time = time.time()
                duration = end_time - start_time
                memory_after = (
                    monitor.get_current_memory_mb() if include_memory else 0.0
                )

                # Add function-specific metadata
                full_metadata = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs),
                }
                if metadata:
                    full_metadata.update(metadata)

                monitor.record_metric(
                    name=operation_name,
                    duration=duration,
                    memory_before=memory_before,
                    memory_after=memory_after,
                    metadata=full_metadata,
                )

        return wrapper

    return decorator


@contextmanager
def memory_tracker(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Context manager for tracking memory usage during operations.

    Args:
        operation_name: Name of the operation being tracked
        metadata: Additional metadata about the operation
    """
    monitor = get_performance_monitor()
    start_time = time.time()
    memory_before = monitor.get_current_memory_mb()

    try:
        yield monitor
    finally:
        end_time = time.time()
        duration = end_time - start_time
        memory_after = monitor.get_current_memory_mb()

        monitor.record_metric(
            name=operation_name,
            duration=duration,
            memory_before=memory_before,
            memory_after=memory_after,
            metadata=metadata or {},
        )


def cache_metrics(cache_name: str):
    """
    Decorator for tracking cache performance metrics.

    Args:
        cache_name: Name of the cache being monitored
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            start_time = time.time()

            # Check if this is a cache hit or miss based on return value
            # This is a simplified approach - real implementation might need
            # more sophisticated cache hit/miss detection
            result = func(*args, **kwargs)

            duration = time.time() - start_time

            # Record cache operation
            metadata = {
                "cache_name": cache_name,
                "operation_type": "cache_access",
                "result_type": type(result).__name__,
            }

            monitor.record_metric(
                name=f"cache.{cache_name}",
                duration=duration,
                memory_before=0,  # Cache operations typically don't track memory
                memory_after=0,
                metadata=metadata,
            )

            return result

        return wrapper

    return decorator


class BatchPerformanceAnalyzer:
    """Analyzer for batch processing performance patterns."""

    def __init__(self, monitor: PerformanceMonitor):
        """Initialize with performance monitor."""
        self.monitor = monitor


    def _generate_batch_recommendations(
        self, avg_duration: float, avg_memory_delta: float, outlier_count: int
    ) -> List[str]:
        """Generate performance recommendations based on analysis."""
        recommendations = []

        if avg_duration > 2.0:
            recommendations.append(
                "Consider reducing batch size or optimizing batch processing logic"
            )

        if avg_memory_delta > 100:  # 100MB
            recommendations.append(
                "High memory usage detected - consider memory optimization strategies"
            )

        if outlier_count > 0:
            recommendations.append(
                "Performance inconsistency detected - investigate outlier operations"
            )

        if not recommendations:
            recommendations.append("Batch performance appears optimal")

        return recommendations


# Global performance monitor instance
_global_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def configure_performance_monitoring(
    max_metrics: int = 10000,
    slow_threshold: float = None,
    very_slow_threshold: float = None,
) -> None:
    """
    Configure global performance monitoring.

    Args:
        max_metrics: Maximum metrics to store
        slow_threshold: Threshold for slow operations (seconds), None to use config
        very_slow_threshold: Threshold for very slow operations (seconds), None to use config
    """
    global _global_monitor
    _global_monitor = PerformanceMonitor(max_metrics)
    _global_monitor.set_thresholds(slow_threshold, very_slow_threshold)
