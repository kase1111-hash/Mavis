"""Tests for mavis.song_editor -- song creation, validation, and community library."""

import os
import tempfile

from mavis.song_editor import CommunityLibrary, SongDraft


def test_draft_validate_valid():
    draft = SongDraft(title="My Song", bpm=120, difficulty="medium", sheet_text="hello world")
    assert draft.validate() == []


def test_draft_validate_missing_title():
    draft = SongDraft(title="", bpm=120, difficulty="medium", sheet_text="hello")
    errors = draft.validate()
    assert any("Title" in e for e in errors)


def test_draft_validate_bad_bpm():
    draft = SongDraft(title="Song", bpm=10, difficulty="medium", sheet_text="hello")
    errors = draft.validate()
    assert any("BPM" in e for e in errors)


def test_draft_validate_bad_difficulty():
    draft = SongDraft(title="Song", bpm=120, difficulty="extreme", sheet_text="hello")
    errors = draft.validate()
    assert any("Difficulty" in e or "difficulty" in e for e in errors)


def test_draft_validate_empty_text():
    draft = SongDraft(title="Song", bpm=120, difficulty="easy", sheet_text="")
    errors = draft.validate()
    assert any("Sheet Text" in e for e in errors)


def test_draft_validate_text_too_long():
    draft = SongDraft(title="Song", bpm=120, difficulty="easy", sheet_text="x" * 5001)
    errors = draft.validate()
    assert any("too long" in e for e in errors)


def test_draft_to_song():
    draft = SongDraft(title="Test", bpm=100, difficulty="easy", sheet_text="hello WORLD")
    song = draft.to_song()
    assert song.title == "Test"
    assert song.bpm == 100
    assert len(song.tokens) > 0


def test_draft_to_json():
    draft = SongDraft(
        title="Test", bpm=100, difficulty="easy",
        sheet_text="hello", author="Alice", tags=["test"],
    )
    data = draft.to_json()
    assert data["title"] == "Test"
    assert data["author"] == "Alice"
    assert "tokens" in data
    assert data["tags"] == ["test"]


def test_draft_save():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        draft = SongDraft(title="Test", bpm=120, difficulty="easy", sheet_text="hello")
        draft.save(path)
        assert os.path.isfile(path)
    finally:
        os.unlink(path)


def test_community_submit():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        draft = SongDraft(title="Community Song", bpm=120, difficulty="easy", sheet_text="hello world")
        entry = lib.submit(draft, author="Alice")
        assert entry.entry_id
        assert entry.author == "Alice"
        assert lib.entry_count() == 1
    finally:
        os.unlink(path)


def test_community_submit_invalid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        draft = SongDraft(title="", bpm=120, difficulty="easy", sheet_text="hello")
        try:
            lib.submit(draft)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
    finally:
        os.unlink(path)


def test_community_browse():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        for i in range(5):
            draft = SongDraft(
                title=f"Song {i}", bpm=120, difficulty="easy", sheet_text=f"text {i}"
            )
            lib.submit(draft, author="Alice")
        entries = lib.browse(limit=3)
        assert len(entries) == 3
    finally:
        os.unlink(path)


def test_community_browse_by_difficulty():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        lib.submit(SongDraft(title="Easy", bpm=120, difficulty="easy", sheet_text="hello"))
        lib.submit(SongDraft(title="Hard", bpm=120, difficulty="hard", sheet_text="hello"))
        easy = lib.browse(difficulty="easy")
        assert len(easy) == 1
        assert easy[0].song_data["title"] == "Easy"
    finally:
        os.unlink(path)


def test_community_rate():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        entry = lib.submit(SongDraft(title="Song", bpm=120, difficulty="easy", sheet_text="hi"))
        assert lib.rate(entry.entry_id, 5)
        assert lib.rate(entry.entry_id, 3)
        fetched = lib.get_entry(entry.entry_id)
        assert fetched.average_rating == 4.0
        assert fetched.rating_count == 2
    finally:
        os.unlink(path)


def test_community_rate_invalid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        entry = lib.submit(SongDraft(title="Song", bpm=120, difficulty="easy", sheet_text="hi"))
        assert not lib.rate(entry.entry_id, 0)  # out of range
        assert not lib.rate(entry.entry_id, 6)  # out of range
        assert not lib.rate("nonexistent", 3)
    finally:
        os.unlink(path)


def test_community_flag():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        entry = lib.submit(SongDraft(title="Bad Song", bpm=120, difficulty="easy", sheet_text="bad"))
        lib.flag(entry.entry_id)
        lib.flag(entry.entry_id)
        fetched = lib.get_entry(entry.entry_id)
        assert fetched.flags == 2
        assert fetched.approved  # Not yet at threshold
    finally:
        os.unlink(path)


def test_community_flag_auto_hide():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        entry = lib.submit(SongDraft(title="Spam", bpm=120, difficulty="easy", sheet_text="spam"))
        for _ in range(3):
            lib.flag(entry.entry_id)
        fetched = lib.get_entry(entry.entry_id)
        assert not fetched.approved
        # Flagged songs should not appear in browse
        visible = lib.browse()
        assert len(visible) == 0
    finally:
        os.unlink(path)


def test_community_sort_by_rating():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib = CommunityLibrary(path=path)
        e1 = lib.submit(SongDraft(title="Low", bpm=120, difficulty="easy", sheet_text="a"))
        e2 = lib.submit(SongDraft(title="High", bpm=120, difficulty="easy", sheet_text="b"))
        lib.rate(e1.entry_id, 2)
        lib.rate(e2.entry_id, 5)
        entries = lib.browse(sort_by="rating")
        assert entries[0].song_data["title"] == "High"
    finally:
        os.unlink(path)


def test_community_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        lib1 = CommunityLibrary(path=path)
        lib1.submit(SongDraft(title="Persistent", bpm=120, difficulty="easy", sheet_text="hi"))
        lib2 = CommunityLibrary(path=path)
        assert lib2.entry_count() == 1
    finally:
        os.unlink(path)
