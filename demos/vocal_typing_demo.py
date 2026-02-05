#!/usr/bin/env python3
"""Non-interactive pipeline demonstration.

Feeds a hardcoded Sheet Text string through the Mavis pipeline and
prints buffer states and phoneme events to the terminal in real time.
"""

import sys
import time

sys.path.insert(0, ".")

from mavis.config import LAPTOP_CPU, MavisConfig
from mavis.pipeline import create_pipeline
from mavis.scoring import ScoreTracker


def bar(level: float, width: int = 20) -> str:
    """Render a horizontal bar: [████░░░░░░]"""
    filled = int(level * width)
    empty = width - filled
    return "[" + "\u2588" * filled + "\u2591" * empty + "]"


def status_color(status: str) -> str:
    """ANSI color prefix for buffer status."""
    colors = {"underflow": "\033[91m", "optimal": "\033[92m", "overflow": "\033[93m"}
    return colors.get(status, "")


RESET = "\033[0m"

DEMO_TEXT = "the SUN... is falling _down_ and RISING [again]"


def main():
    print("=" * 60)
    print("  Mavis Pipeline Demo")
    print("  Sheet Text: " + repr(DEMO_TEXT))
    print("=" * 60)
    print()

    config = MavisConfig(hardware=LAPTOP_CPU, llm_backend="mock", tts_backend="mock")
    pipe = create_pipeline(config)
    tracker = ScoreTracker()

    # Simulate typing at ~60 WPM (1 char every 200ms, 5 chars/word)
    char_delay = 0.15

    # Feed all characters with a simulated delay
    chars_fed = 0
    total = len(DEMO_TEXT)

    print(f"Simulating typing at ~60 WPM ({total} characters)...\n")

    for char in DEMO_TEXT:
        mods = {"shift": char.isupper(), "ctrl": False, "alt": False}
        pipe.feed(char, mods)
        chars_fed += 1

        # Tick the pipeline
        state = pipe.tick()
        buf_state = pipe.output_buffer.state()
        tracker.on_tick(buf_state)

        # Display
        in_bar = bar(state["input_buffer_level"])
        out_bar = bar(state["output_buffer_level"])
        st = state["output_buffer_status"]
        color = status_color(st)

        phoneme_str = state["last_phoneme"] or "-"
        token_str = " ".join(state["last_tokens"][:3]) if state["last_tokens"] else "-"

        sys.stdout.write(
            f"\r  Typed: {chars_fed:3d}/{total}  "
            f"IN {in_bar}  "
            f"OUT {color}{out_bar} {st:10s}{RESET}  "
            f"Token: {token_str:12s}  "
            f"Phoneme: {phoneme_str:4s}"
        )
        sys.stdout.flush()

        time.sleep(char_delay)

    # Drain remaining output buffer
    print("\n\n  Draining output buffer...")
    drain_ticks = 0
    while pipe.output_buffer.size() > 0 and drain_ticks < 200:
        state = pipe.tick()
        buf_state = pipe.output_buffer.state()
        tracker.on_tick(buf_state)
        drain_ticks += 1

        out_bar = bar(state["output_buffer_level"])
        st = state["output_buffer_status"]
        color = status_color(st)
        phoneme_str = state["last_phoneme"] or "-"

        sys.stdout.write(
            f"\r  Drain: {color}{out_bar} {st:10s}{RESET}  "
            f"Phoneme: {phoneme_str:4s}  "
            f"Remaining: {state['output_buffer_size']:3d}"
        )
        sys.stdout.flush()
        time.sleep(0.05)

    print("\n")
    print("=" * 60)
    print(f"  Score: {tracker.score()}  Grade: {tracker.grade()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
