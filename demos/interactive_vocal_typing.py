#!/usr/bin/env python3
"""Interactive vocal typing demo with buffer visualization and sustain bars.

Uses curses for non-blocking keyboard input and live buffer display.
Press Esc or Ctrl+C to exit.

Optional: pass a song JSON path as argument to play with scoring.
  python3 demos/interactive_vocal_typing.py songs/twinkle.json
"""

import curses
import os
import sys
import time

sys.path.insert(0, ".")

from mavis.config import LAPTOP_CPU, MavisConfig
from mavis.output_buffer import BufferState
from mavis.pipeline import create_pipeline
from mavis.scoring import ScoreTracker
from mavis.songs import Song, load_song

# Sustain bar config
SUSTAIN_MAX_WIDTH = 30
SUSTAIN_CHAR_FILL = "\u2588"
SUSTAIN_CHAR_PARTIAL = "\u2593"
SUSTAIN_CHAR_EMPTY = "\u2591"


def draw_bar(win, y, x, level, width, label=""):
    """Draw a horizontal bar with optional label."""
    filled = int(level * width)
    empty = width - filled
    bar_str = SUSTAIN_CHAR_FILL * filled + SUSTAIN_CHAR_EMPTY * empty
    try:
        win.addstr(y, x, f"{label}[{bar_str}] {level:.0%}")
    except curses.error:
        pass


def draw_sustain_bar(win, y, x, hold_ms, target_ms):
    """Draw a sustain bar that grows as the player holds a note.

    Color coding:
      Green:  within 20% of target duration
      Yellow: within 50% of target duration
      Red:    outside 50%
    """
    ratio = min(hold_ms / target_ms, 1.0) if target_ms > 0 else 0.0
    filled = int(ratio * SUSTAIN_MAX_WIDTH)
    empty = SUSTAIN_MAX_WIDTH - filled

    # Determine quality color
    diff = abs(hold_ms - target_ms) / target_ms if target_ms > 0 else 1.0
    if diff <= 0.2:
        color = curses.color_pair(1)  # green
    elif diff <= 0.5:
        color = curses.color_pair(2)  # yellow
    else:
        color = curses.color_pair(3)  # red

    try:
        win.addstr(y, x, "Sustain: [", curses.A_BOLD)
        win.addstr(SUSTAIN_CHAR_FILL * filled, color | curses.A_BOLD)
        win.addstr(SUSTAIN_CHAR_EMPTY * empty)
        win.addstr(f"] {hold_ms:.0f}ms / {target_ms:.0f}ms")
    except curses.error:
        pass


def status_attr(status):
    """Return curses attribute for buffer status."""
    if status == "optimal":
        return curses.color_pair(1)
    elif status == "overflow":
        return curses.color_pair(2)
    else:
        return curses.color_pair(3)


def main(stdscr):
    # Setup curses
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(33)  # ~30 FPS

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)

    # Load song if provided
    song = None
    song_tokens_idx = 0
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        song = load_song(sys.argv[1])

    config = MavisConfig(hardware=LAPTOP_CPU, llm_backend="mock", tts_backend="mock")
    pipe = create_pipeline(config)
    tracker = ScoreTracker()

    typed_text = []
    phonemes_played = []
    sustain_start = None
    sustain_active = False
    sustain_hold_ms = 0.0
    sustain_target_ms = 400.0  # default target for sustain
    dot_count = 0

    running = True
    frame = 0

    while running:
        frame += 1
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        # Header
        title = "Mavis Interactive Vocal Typing"
        if song:
            title += f" - {song.title}"
        try:
            stdscr.addstr(0, 0, title, curses.A_BOLD | curses.color_pair(4))
            stdscr.addstr(1, 0, "-" * min(w - 1, 60))
        except curses.error:
            pass

        # Read keyboard input
        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        if key == 27:  # Esc
            running = False
            continue

        if key != -1 and key < 256 and key != curses.ERR:
            char = chr(key)
            shift = char.isupper()
            ctrl = key < 32  # rough ctrl detection
            mods = {"shift": shift, "ctrl": ctrl, "alt": False}
            pipe.feed(char, mods)
            typed_text.append(char)

            # Track sustain (dots)
            if char == ".":
                dot_count += 1
                if dot_count == 3:
                    sustain_active = True
                    sustain_start = time.monotonic()
                    dot_count = 0
            else:
                if sustain_active:
                    sustain_hold_ms = (time.monotonic() - sustain_start) * 1000
                    sustain_active = False
                dot_count = 0

        # Update sustain timer if held
        if sustain_active and sustain_start:
            sustain_hold_ms = (time.monotonic() - sustain_start) * 1000

        # Tick the pipeline
        state = pipe.tick()
        buf_state = pipe.output_buffer.state()
        tracker.on_tick(buf_state)

        if state["last_phoneme"]:
            phonemes_played.append(state["last_phoneme"])

        # Song text display
        row = 3
        if song:
            try:
                stdscr.addstr(row, 0, "Sheet Text:", curses.A_BOLD)
            except curses.error:
                pass
            row += 1
            # Show sheet text with wrapping
            sheet_lines = song.sheet_text.split("\n")
            for line in sheet_lines:
                try:
                    stdscr.addstr(row, 2, line[:w - 4])
                except curses.error:
                    pass
                row += 1
            row += 1

        # Typed text
        try:
            stdscr.addstr(row, 0, "Your input:", curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        display_typed = "".join(typed_text[-(w - 4):])
        try:
            stdscr.addstr(row, 2, display_typed)
        except curses.error:
            pass
        row += 2

        # Buffer visualizations
        try:
            stdscr.addstr(row, 0, "Buffers:", curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        draw_bar(stdscr, row, 2, state["input_buffer_level"], 20, "IN  ")
        row += 1

        st = state["output_buffer_status"]
        attr = status_attr(st)
        draw_bar(stdscr, row, 2, state["output_buffer_level"], 20, "OUT ")
        try:
            stdscr.addstr(row, 32, f" {st}", attr | curses.A_BOLD)
        except curses.error:
            pass
        row += 2

        # Sustain bar
        if sustain_active or sustain_hold_ms > 0:
            draw_sustain_bar(stdscr, row, 2, sustain_hold_ms, sustain_target_ms)
            row += 2

        # Current phoneme
        ph = state["last_phoneme"] or "-"
        try:
            stdscr.addstr(row, 0, f"Phoneme: {ph}", curses.A_BOLD)
        except curses.error:
            pass
        row += 1

        tokens_str = " ".join(state["last_tokens"][:5]) if state["last_tokens"] else "-"
        try:
            stdscr.addstr(row, 0, f"Tokens:  {tokens_str}")
        except curses.error:
            pass
        row += 2

        # Score
        try:
            stdscr.addstr(row, 0, f"Score: {tracker.score()}  Grade: {tracker.grade()}",
                          curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        try:
            stdscr.addstr(row, 0, f"Phonemes played: {len(phonemes_played)}")
        except curses.error:
            pass
        row += 2

        # Instructions
        try:
            stdscr.addstr(min(row, h - 2), 0,
                          "Type to sing! CAPS=loud  _word_=soft  ...=sustain  "
                          "[word]=harmony  Esc=quit")
        except curses.error:
            pass

        stdscr.refresh()

    # Final score screen
    stdscr.erase()
    stdscr.nodelay(False)
    try:
        stdscr.addstr(2, 0, "Performance Complete!", curses.A_BOLD | curses.color_pair(4))
        stdscr.addstr(4, 0, f"Final Score: {tracker.score()}")
        stdscr.addstr(5, 0, f"Grade: {tracker.grade()}")
        stdscr.addstr(6, 0, f"Phonemes played: {len(phonemes_played)}")
        stdscr.addstr(7, 0, f"Characters typed: {len(typed_text)}")
        stdscr.addstr(9, 0, "Press any key to exit...")
    except curses.error:
        pass
    stdscr.refresh()
    stdscr.getch()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
