"""Output buffer -- FIFO queue of PhonemeEvents awaiting audio synthesis.

Buffer level is the core game mechanic: underflow = voice cracks,
optimal = smooth output, overflow = pitch strain.
"""

import time
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

from mavis.llm_processor import PhonemeEvent


@dataclass
class BufferState:
    """Snapshot of the output buffer status."""

    level: float  # 0.0 - 1.0
    status: str  # "underflow" | "optimal" | "overflow"
    drain_rate: float  # phonemes consumed per second
    fill_rate: float  # phonemes received per second


class OutputBuffer:
    """FIFO buffer of PhonemeEvents with rate tracking.

    Thresholds:
        level < 0.2  -> underflow
        0.2 <= level <= 0.8 -> optimal
        level > 0.8 -> overflow
    """

    def __init__(self, capacity: int = 128):
        self.capacity = capacity
        self._buffer: deque = deque()
        self._push_times: List[float] = []
        self._pop_times: List[float] = []
        self._rate_window_s = 2.0

    def push(self, events: List[PhonemeEvent]) -> None:
        """Add phoneme events to the queue."""
        now = time.monotonic()
        for ev in events:
            if len(self._buffer) < self.capacity:
                self._buffer.append(ev)
                self._push_times.append(now)

    def pop(self) -> Optional[PhonemeEvent]:
        """Remove and return the next phoneme event, or None if empty."""
        if not self._buffer:
            return None
        self._pop_times.append(time.monotonic())
        return self._buffer.popleft()

    def state(self) -> BufferState:
        """Return current buffer state with fill level and rates."""
        level = len(self._buffer) / self.capacity if self.capacity > 0 else 0.0

        if level < 0.2:
            status = "underflow"
        elif level > 0.8:
            status = "overflow"
        else:
            status = "optimal"

        now = time.monotonic()
        fill_rate = self._calc_rate(self._push_times, now)
        drain_rate = self._calc_rate(self._pop_times, now)

        return BufferState(
            level=level,
            status=status,
            drain_rate=drain_rate,
            fill_rate=fill_rate,
        )

    def size(self) -> int:
        """Current number of events in the buffer."""
        return len(self._buffer)

    def clear(self) -> None:
        """Remove all events."""
        self._buffer.clear()

    def _calc_rate(self, timestamps: List[float], now: float) -> float:
        """Calculate events per second over the sliding window."""
        cutoff = now - self._rate_window_s
        # Prune old entries
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)
        if not timestamps:
            return 0.0
        elapsed = now - timestamps[0]
        if elapsed <= 0:
            return float(len(timestamps))
        return len(timestamps) / elapsed
