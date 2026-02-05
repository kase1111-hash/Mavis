"""Input buffer for capturing and queuing keystrokes."""

import time
from collections import deque
from typing import Dict, List, Optional


class InputBuffer:
    """FIFO queue for keyboard input that feeds into the Sheet Text parser.

    Each buffered item stores the character, modifier key state, and timestamp.
    When the buffer exceeds capacity, the oldest items are silently dropped.
    """

    def __init__(self, capacity: int = 256):
        self.capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)

    def push(self, char: str, modifiers: Optional[Dict[str, bool]] = None) -> None:
        """Append a character with modifier state to the buffer."""
        mods = modifiers or {}
        item = {
            "char": char,
            "shift": mods.get("shift", False),
            "ctrl": mods.get("ctrl", False),
            "alt": mods.get("alt", False),
            "timestamp_ms": int(time.time() * 1000),
        }
        self._buffer.append(item)

    def peek(self, n: int) -> List[Dict]:
        """Look at the next N characters without consuming them."""
        items = list(self._buffer)
        return items[:n]

    def consume(self, n: int) -> List[Dict]:
        """Remove and return the next N characters from the buffer."""
        result = []
        for _ in range(min(n, len(self._buffer))):
            result.append(self._buffer.popleft())
        return result

    def level(self) -> float:
        """Return buffer fill ratio (0.0 = empty, 1.0 = full)."""
        if self.capacity == 0:
            return 0.0
        return len(self._buffer) / self.capacity

    def size(self) -> int:
        """Return current number of items in the buffer."""
        return len(self._buffer)

    def clear(self) -> None:
        """Remove all items from the buffer."""
        self._buffer.clear()
