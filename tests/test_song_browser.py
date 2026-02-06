"""Tests for mavis.song_browser."""

import os

from mavis.song_browser import (
    browse_songs,
    format_song_list,
    group_by_difficulty,
    song_summary,
)
from mavis.songs import Song, list_songs


def test_browse_songs_returns_all():
    songs = browse_songs("songs")
    assert len(songs) == 10  # twinkle + 9 new songs


def test_browse_songs_filter_easy():
    songs = browse_songs("songs", difficulty="easy")
    assert all(s.difficulty == "easy" for s in songs)
    assert len(songs) == 3  # twinkle, mary_lamb, row_boat


def test_browse_songs_filter_medium():
    songs = browse_songs("songs", difficulty="medium")
    assert all(s.difficulty == "medium" for s in songs)
    assert len(songs) == 4  # amazing_grace, bohemian, hallelujah, somewhere_rainbow


def test_browse_songs_filter_hard():
    songs = browse_songs("songs", difficulty="hard")
    assert all(s.difficulty == "hard" for s in songs)
    assert len(songs) == 3  # dont_stop, nessun_dorma, rap_god


def test_browse_songs_sorted_by_difficulty():
    songs = browse_songs("songs")
    difficulties = [s.difficulty for s in songs]
    # Easy comes before medium, medium before hard
    seen_medium = False
    seen_hard = False
    for d in difficulties:
        if d == "medium":
            seen_medium = True
        if d == "hard":
            seen_hard = True
        if d == "easy":
            assert not seen_medium, "Easy should come before medium"
            assert not seen_hard, "Easy should come before hard"


def test_browse_songs_nonexistent_dir():
    songs = browse_songs("/nonexistent")
    assert songs == []


def test_group_by_difficulty():
    songs = list_songs("songs")
    groups = group_by_difficulty(songs)
    assert "easy" in groups
    assert "medium" in groups
    assert "hard" in groups
    total = sum(len(v) for v in groups.values())
    assert total == len(songs)


def test_song_summary():
    song = Song(title="Test Song", bpm=120, difficulty="easy", sheet_text="hello",
                tokens=[], song_id="test")
    summary = song_summary(song)
    assert "Test Song" in summary
    assert "120 bpm" in summary
    assert "EASY" in summary


def test_format_song_list():
    songs = list_songs("songs")
    text = format_song_list(songs)
    assert "1." in text
    assert len(text.strip().split("\n")) == len(songs)


def test_format_song_list_empty():
    text = format_song_list([])
    assert "no songs" in text.lower()
