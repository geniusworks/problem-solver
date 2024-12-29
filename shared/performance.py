"""Performance monitoring utilities."""

import time
import psutil
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Memory statistics for a process."""
    initial_rss: int  # Initial Resident Set Size in bytes
    peak_rss: int    # Peak Resident Set Size in bytes
    final_rss: int   # Final Resident Set Size in bytes
    increase: int    # Increase in RSS from initial to final

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary with human-readable values."""
        return {
            "initial_memory_mb": round(self.initial_rss / (1024 * 1024), 2),
            "peak_memory_mb": round(self.peak_rss / (1024 * 1024), 2),
            "final_memory_mb": round(self.final_rss / (1024 * 1024), 2),
            "memory_increase_mb": round(self.increase / (1024 * 1024), 2)
        }

@dataclass
class PerformanceMetrics:
    """Performance metrics for code execution."""
    execution_time: float      # Total execution time in seconds
    memory_stats: MemoryStats  # Memory statistics
    cpu_percent: float        # Average CPU usage percentage

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "execution_time_sec": round(self.execution_time, 3),
            "memory_stats": self.memory_stats.to_dict(),
            "cpu_percent": round(self.cpu_percent, 1)
        }

class PerformanceMonitor:
    """Monitors code performance metrics."""

    def __init__(self):
        """Initialize the performance monitor."""
        self.process = psutil.Process()
        self._reset()

    def _reset(self):
        """Reset monitoring state."""
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.initial_memory: Optional[int] = None
        self.peak_memory: int = 0
        self.cpu_samples: list[float] = []

    def _update_peak_memory(self):
        """Update peak memory usage."""
        current = self.process.memory_info().rss
        self.peak_memory = max(self.peak_memory, current)

    def _sample_cpu(self):
        """Sample current CPU usage."""
        self.cpu_samples.append(self.process.cpu_percent())

    @contextmanager
    def monitor(self):
        """Context manager for monitoring code execution.
        
        Usage:
            monitor = PerformanceMonitor()
            with monitor.monitor():
                # Code to monitor
            metrics = monitor.get_metrics()
        """
        try:
            self._reset()
            self.start_time = time.time()
            self.initial_memory = self.process.memory_info().rss
            
            yield
            
        finally:
            self.end_time = time.time()
            final_memory = self.process.memory_info().rss
            self._update_peak_memory()
            self._sample_cpu()

            # Calculate metrics
            execution_time = self.end_time - self.start_time
            memory_stats = MemoryStats(
                initial_rss=self.initial_memory,
                peak_rss=self.peak_memory,
                final_rss=final_memory,
                increase=final_memory - self.initial_memory
            )
            cpu_percent = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0

            self.metrics = PerformanceMetrics(
                execution_time=execution_time,
                memory_stats=memory_stats,
                cpu_percent=cpu_percent
            )

    def get_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the collected performance metrics.
        
        Returns:
            PerformanceMetrics if monitoring was completed, None otherwise
        """
        return getattr(self, 'metrics', None)
