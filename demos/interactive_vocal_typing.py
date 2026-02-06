#!/usr/bin/env python3
"""Interactive vocal typing demo with buffer visualization and sustain bars.

Uses curses for non-blocking keyboard input and live buffer display.
Press Esc or Ctrl+C to exit.

Phase 2 features: song browser, difficulty selection, voice customization,
leaderboard display, and tutorial access.

Usage:
  python3 demos/interactive_vocal_typing.py                   # Main menu
  python3 demos/interactive_vocal_typing.py songs/twinkle.json  # Direct play
"""

import curses
import os
import sys
import time

sys.path.insert(0, ".")

from mavis.config import LAPTOP_CPU, MavisConfig
from mavis.difficulty import DIFFICULTY_PRESETS, DifficultySettings, list_difficulties
from mavis.leaderboard import Leaderboard, LeaderboardEntry, get_default_leaderboard
from mavis.output_buffer import BufferState
from mavis.pipeline import create_pipeline
from mavis.scoring import ScoreTracker
from mavis.song_browser import browse_songs, format_song_list, group_by_difficulty
from mavis.songs import Song, load_song, list_songs
from mavis.tutorial import (
    LESSONS,
    TutorialLesson,
    TutorialProgress,
    format_lesson_list,
    get_lesson,
)
from mavis.voice import VOICES, VoiceProfile, get_voice, list_voices

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
    """Draw a sustain bar that grows as the player holds a note."""
    ratio = min(hold_ms / target_ms, 1.0) if target_ms > 0 else 0.0
    filled = int(ratio * SUSTAIN_MAX_WIDTH)
    empty = SUSTAIN_MAX_WIDTH - filled

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


# --- Menu helpers ---

def draw_menu(stdscr, title, items, selected):
    """Draw a numbered menu and return the screen row after the last item."""
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(0, 0, title, curses.A_BOLD | curses.color_pair(4))
        stdscr.addstr(1, 0, "-" * min(w - 1, 60))
    except curses.error:
        pass
    for i, item in enumerate(items):
        attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
        try:
            stdscr.addstr(3 + i, 2, f" {i + 1}. {item} ", attr)
        except curses.error:
            pass
    return 3 + len(items) + 1


def menu_loop(stdscr, title, items):
    """Run a menu loop and return the index selected, or -1 for Esc."""
    selected = 0
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        row = draw_menu(stdscr, title, items, selected)
        try:
            stdscr.addstr(row + 1, 0, "Up/Down to navigate, Enter to select, Esc to go back")
        except curses.error:
            pass
        stdscr.refresh()
        key = stdscr.getch()
        if key == 27:
            return -1
        elif key == curses.KEY_UP:
            selected = (selected - 1) % len(items)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(items)
        elif key in (curses.KEY_ENTER, 10, 13):
            return selected
        elif ord("1") <= key <= ord("9"):
            idx = key - ord("1")
            if 0 <= idx < len(items):
                return idx


# --- Main menu ---

def main_menu(stdscr):
    """Show the main menu and return the user's choice."""
    items = [
        "Play a Song",
        "Tutorial",
        "Leaderboard",
        "Settings (Difficulty / Voice)",
        "Quit",
    ]
    return menu_loop(stdscr, "Mavis - Vocal Typing Instrument", items)


# --- Song browser ---

def song_browser_menu(stdscr, difficulty_filter=None):
    """Show the song browser and return the selected Song or None."""
    songs = browse_songs("songs", difficulty=difficulty_filter)
    if not songs:
        stdscr.erase()
        try:
            stdscr.addstr(2, 0, "No songs found in songs/ directory.")
            stdscr.addstr(4, 0, "Press any key...")
        except curses.error:
            pass
        stdscr.refresh()
        stdscr.getch()
        return None
    items = []
    for s in songs:
        diff = s.difficulty.upper().ljust(6)
        items.append(f"[{diff}] {s.title} ({s.bpm} bpm, {len(s.tokens)} tokens)")
    idx = menu_loop(stdscr, "Select a Song", items)
    if idx < 0:
        return None
    return songs[idx]


# --- Difficulty / Voice settings ---

def settings_menu(stdscr):
    """Settings menu for difficulty and voice. Returns (difficulty_name, voice_name)."""
    diff_name = "medium"
    voice_name = "default"

    while True:
        items = [
            f"Difficulty: {diff_name}",
            f"Voice: {voice_name}",
            "Back to Main Menu",
        ]
        idx = menu_loop(stdscr, "Settings", items)
        if idx < 0 or idx == 2:
            return diff_name, voice_name
        elif idx == 0:
            diffs = list(DIFFICULTY_PRESETS.keys())
            diff_items = []
            for d in diffs:
                ds = DIFFICULTY_PRESETS[d]
                diff_items.append(f"{ds.name} - {ds.description}")
            di = menu_loop(stdscr, "Select Difficulty", diff_items)
            if di >= 0:
                diff_name = diffs[di]
        elif idx == 1:
            voice_keys = list(VOICES.keys())
            voice_items = []
            for vk in voice_keys:
                v = VOICES[vk]
                voice_items.append(f"{v.name} ({v.base_pitch_hz:.0f} Hz) - {v.description}")
            vi = menu_loop(stdscr, "Select Voice", voice_items)
            if vi >= 0:
                voice_name = voice_keys[vi]


# --- Leaderboard display ---

def leaderboard_menu(stdscr):
    """Show the leaderboard."""
    lb = get_default_leaderboard()
    all_scores = lb.get_all_scores(limit_per_song=5)

    stdscr.erase()
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(0, 0, "Leaderboard", curses.A_BOLD | curses.color_pair(4))
        stdscr.addstr(1, 0, "-" * min(w - 1, 60))
    except curses.error:
        pass

    row = 3
    if not all_scores:
        try:
            stdscr.addstr(row, 2, "(no scores recorded yet)")
        except curses.error:
            pass
        row += 2
    else:
        for song_id, entries in all_scores.items():
            try:
                stdscr.addstr(row, 0, f"  {song_id}:", curses.A_BOLD)
            except curses.error:
                pass
            row += 1
            for i, e in enumerate(entries, 1):
                name = e.get("player_name", "???")
                score = e.get("score", 0)
                grade = e.get("grade", "?")
                try:
                    stdscr.addstr(row, 4, f"{i}. {name:<12s} {score:>8d}  [{grade}]")
                except curses.error:
                    pass
                row += 1
            row += 1

    try:
        stdscr.addstr(min(row, h - 2), 0, "Press any key to return...")
    except curses.error:
        pass
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


# --- Tutorial mode ---

def tutorial_menu(stdscr):
    """Show the tutorial lesson list and return the selected lesson or None."""
    progress = TutorialProgress()
    items = []
    for lesson in LESSONS:
        marker = "[ ]"
        if progress.is_completed(lesson.lesson_id):
            grade = progress.best_grade(lesson.lesson_id)
            marker = f"[{grade}]"
        items.append(f"{marker} {lesson.title} - {lesson.description}")
    items.append("Back to Main Menu")

    idx = menu_loop(stdscr, "Tutorial", items)
    if idx < 0 or idx == len(LESSONS):
        return None
    return LESSONS[idx]


# --- Gameplay loop ---

def play_game(stdscr, song, difficulty_name="medium", voice_name="default"):
    """Run the main gameplay loop for a song or tutorial lesson."""
    config = MavisConfig(
        hardware=LAPTOP_CPU,
        llm_backend="mock",
        tts_backend="mock",
        difficulty_name=difficulty_name,
        voice_name=voice_name,
    )
    pipe = create_pipeline(config)
    tracker = ScoreTracker()

    typed_text = []
    phonemes_played = []
    sustain_start = None
    sustain_active = False
    sustain_hold_ms = 0.0
    sustain_target_ms = 400.0
    dot_count = 0

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(33)

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
        if pipe.difficulty:
            title += f" [{pipe.difficulty.name}]"
        if pipe.voice:
            title += f" ({pipe.voice.name})"
        try:
            stdscr.addstr(0, 0, title[:w - 1], curses.A_BOLD | curses.color_pair(4))
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
            ctrl = key < 32
            mods = {"shift": shift, "ctrl": ctrl, "alt": False}
            pipe.feed(char, mods)
            typed_text.append(char)

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

    # Return final results
    return tracker.score(), tracker.grade(), len(phonemes_played), len(typed_text)


def show_results(stdscr, score, grade, phonemes, chars, song=None):
    """Show the final score screen after a performance."""
    stdscr.erase()
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    try:
        stdscr.addstr(2, 0, "Performance Complete!", curses.A_BOLD | curses.color_pair(4))
        if song:
            stdscr.addstr(3, 0, f"Song: {song.title}")
        stdscr.addstr(5, 0, f"Final Score: {score}")
        stdscr.addstr(6, 0, f"Grade: {grade}")
        stdscr.addstr(7, 0, f"Phonemes played: {phonemes}")
        stdscr.addstr(8, 0, f"Characters typed: {chars}")
        stdscr.addstr(10, 0, "Press any key to continue...")
    except curses.error:
        pass
    stdscr.refresh()
    stdscr.getch()

    # Attempt to submit to leaderboard
    if song and score > 0:
        try:
            lb = get_default_leaderboard()
            entry = LeaderboardEntry(
                player_name="Player",
                score=score,
                grade=grade,
                song_id=song.song_id,
                difficulty="medium",
            )
            rank = lb.submit(entry)
            if rank > 0:
                stdscr.erase()
                try:
                    stdscr.addstr(2, 0, f"New high score! Rank #{rank}", curses.A_BOLD)
                    stdscr.addstr(4, 0, "Press any key...")
                except curses.error:
                    pass
                stdscr.refresh()
                stdscr.getch()
        except Exception:
            pass  # Leaderboard is optional


def main(stdscr):
    # Setup curses
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)

    # Check for direct song argument
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        song = load_song(sys.argv[1])
        score, grade, phonemes, chars = play_game(stdscr, song)
        show_results(stdscr, score, grade, phonemes, chars, song)
        return

    # Settings defaults
    difficulty_name = "medium"
    voice_name = "default"

    # Main menu loop
    while True:
        choice = main_menu(stdscr)

        if choice < 0 or choice == 4:  # Quit
            break

        elif choice == 0:  # Play a Song
            song = song_browser_menu(stdscr)
            if song is not None:
                score, grade, phonemes, chars = play_game(
                    stdscr, song, difficulty_name, voice_name
                )
                show_results(stdscr, score, grade, phonemes, chars, song)

        elif choice == 1:  # Tutorial
            lesson = tutorial_menu(stdscr)
            if lesson is not None:
                # Create a pseudo-Song from the lesson
                from mavis.sheet_text import SheetTextToken
                pseudo_song = Song(
                    title=f"Tutorial {lesson.lesson_id}: {lesson.title}",
                    bpm=90,
                    difficulty="easy",
                    sheet_text=lesson.sheet_text,
                    tokens=[],
                    song_id=f"tutorial_{lesson.lesson_id}",
                )
                score, grade, phonemes, chars = play_game(
                    stdscr, pseudo_song, "easy", voice_name
                )
                show_results(stdscr, score, grade, phonemes, chars, pseudo_song)

        elif choice == 2:  # Leaderboard
            leaderboard_menu(stdscr)

        elif choice == 3:  # Settings
            difficulty_name, voice_name = settings_menu(stdscr)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
