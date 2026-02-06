"""Tests for mavis.leaderboard."""

import json
import os
import tempfile

from mavis.leaderboard import Leaderboard, LeaderboardEntry


def _make_lb(tmpdir):
    """Create a leaderboard in a temp directory."""
    path = os.path.join(tmpdir, "lb.json")
    return Leaderboard(path=path, max_entries_per_song=5)


def test_empty_leaderboard():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        assert lb.get_scores("twinkle") == []


def test_submit_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        entry = LeaderboardEntry(
            player_name="Alice",
            score=1000,
            grade="A",
            song_id="twinkle",
            difficulty="medium",
        )
        rank = lb.submit(entry)
        assert rank == 1
        scores = lb.get_scores("twinkle")
        assert len(scores) == 1
        assert scores[0]["player_name"] == "Alice"
        assert scores[0]["score"] == 1000


def test_scores_sorted_descending():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        for score in [500, 1000, 750]:
            entry = LeaderboardEntry(
                player_name="Player",
                score=score,
                grade="B",
                song_id="twinkle",
                difficulty="medium",
            )
            lb.submit(entry)
        scores = lb.get_scores("twinkle")
        score_values = [s["score"] for s in scores]
        assert score_values == sorted(score_values, reverse=True)


def test_max_entries_enforced():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)  # max_entries_per_song=5
        for i in range(10):
            entry = LeaderboardEntry(
                player_name=f"P{i}",
                score=i * 100,
                grade="C",
                song_id="twinkle",
                difficulty="easy",
            )
            lb.submit(entry)
        scores = lb.get_scores("twinkle")
        assert len(scores) == 5
        # Top 5 should be highest scores
        assert scores[0]["score"] == 900


def test_filter_by_difficulty():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        for diff in ["easy", "medium", "hard"]:
            entry = LeaderboardEntry(
                player_name="Player",
                score=100,
                grade="C",
                song_id="twinkle",
                difficulty=diff,
            )
            lb.submit(entry)
        medium = lb.get_scores("twinkle", difficulty="medium")
        assert len(medium) == 1
        assert medium[0]["difficulty"] == "medium"


def test_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "lb.json")
        lb1 = Leaderboard(path=path)
        entry = LeaderboardEntry(
            player_name="Alice", score=999, grade="S",
            song_id="twinkle", difficulty="hard",
        )
        lb1.submit(entry)

        # Reload from same file
        lb2 = Leaderboard(path=path)
        scores = lb2.get_scores("twinkle")
        assert len(scores) == 1
        assert scores[0]["score"] == 999


def test_clear_song():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        for song in ["twinkle", "mary_lamb"]:
            entry = LeaderboardEntry(
                player_name="P", score=100, grade="C",
                song_id=song, difficulty="easy",
            )
            lb.submit(entry)
        lb.clear(song_id="twinkle")
        assert lb.get_scores("twinkle") == []
        assert len(lb.get_scores("mary_lamb")) == 1


def test_clear_all():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        for song in ["twinkle", "mary_lamb"]:
            entry = LeaderboardEntry(
                player_name="P", score=100, grade="C",
                song_id=song, difficulty="easy",
            )
            lb.submit(entry)
        lb.clear()
        assert lb.get_all_scores() == {}


def test_get_all_scores():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        for song in ["twinkle", "mary_lamb"]:
            entry = LeaderboardEntry(
                player_name="P", score=100, grade="C",
                song_id=song, difficulty="easy",
            )
            lb.submit(entry)
        all_scores = lb.get_all_scores()
        assert "twinkle" in all_scores
        assert "mary_lamb" in all_scores


def test_format_scores_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        text = lb.format_scores("twinkle")
        assert "no scores" in text.lower()


def test_format_scores():
    with tempfile.TemporaryDirectory() as tmpdir:
        lb = _make_lb(tmpdir)
        entry = LeaderboardEntry(
            player_name="Alice", score=500, grade="B",
            song_id="twinkle", difficulty="medium",
        )
        lb.submit(entry)
        text = lb.format_scores("twinkle")
        assert "Alice" in text
        assert "500" in text
