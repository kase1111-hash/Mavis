"""Tests for mavis.songs."""

import os

from mavis.songs import Song, list_songs, load_song

SONGS_DIR = os.path.join(os.path.dirname(__file__), "..", "songs")


def test_load_twinkle():
    path = os.path.join(SONGS_DIR, "twinkle.json")
    song = load_song(path)
    assert isinstance(song, Song)
    assert song.title == "Twinkle Twinkle Little Star"
    assert song.bpm == 90
    assert song.difficulty == "easy"
    assert len(song.tokens) == 10
    assert song.song_id == "twinkle"


def test_twinkle_tokens():
    path = os.path.join(SONGS_DIR, "twinkle.json")
    song = load_song(path)
    # First token: TWINKLE -> loud
    assert song.tokens[0].text == "TWINKLE"
    assert song.tokens[0].emphasis == "loud"
    # Third token: little -> soft
    assert song.tokens[2].text == "little"
    assert song.tokens[2].emphasis == "soft"
    # Fourth token: STAR -> loud + sustain
    assert song.tokens[3].text == "STAR"
    assert song.tokens[3].sustain is True


def test_list_songs():
    songs = list_songs(SONGS_DIR)
    assert len(songs) >= 1
    assert any(s.song_id == "twinkle" for s in songs)


def test_list_songs_missing_dir():
    songs = list_songs("/nonexistent/path")
    assert songs == []


def test_sheet_text_present():
    path = os.path.join(SONGS_DIR, "twinkle.json")
    song = load_song(path)
    assert "TWINKLE" in song.sheet_text
    assert "STAR" in song.sheet_text
