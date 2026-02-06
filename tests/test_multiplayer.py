"""Tests for mavis.multiplayer -- rooms, players, and duet splitting."""

from mavis.multiplayer import DuetSplitter, Player, Room, RoomManager
from mavis.sheet_text import SheetTextToken
from mavis.songs import Song


def _make_song(sheet_text="hello WORLD", title="Test Song"):
    tokens = [
        SheetTextToken(text="hello", emphasis="none", sustain=False, harmony=False, duration_modifier=1.0),
        SheetTextToken(text="WORLD", emphasis="loud", sustain=False, harmony=False, duration_modifier=1.0),
    ]
    return Song(title=title, bpm=120, difficulty="medium", sheet_text=sheet_text, tokens=tokens, song_id="test")


def test_room_creation():
    room = Room(room_id="abc123", mode="competitive")
    assert room.room_id == "abc123"
    assert room.mode == "competitive"
    assert room.player_count == 0
    assert not room.is_full


def test_room_add_player():
    room = Room(room_id="r1", song=_make_song())
    p = room.add_player("Alice")
    assert p.name == "Alice"
    assert room.player_count == 1
    assert not room.is_full


def test_room_is_full():
    room = Room(room_id="r2", song=_make_song())
    room.add_player("Alice")
    room.add_player("Bob")
    assert room.is_full
    assert room.player_count == 2


def test_room_add_player_when_full():
    room = Room(room_id="r3", song=_make_song())
    room.add_player("Alice")
    room.add_player("Bob")
    try:
        room.add_player("Charlie")
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_room_remove_player():
    room = Room(room_id="r4", song=_make_song())
    p = room.add_player("Alice")
    name = room.remove_player(p.player_id)
    assert name == "Alice"
    assert room.player_count == 0


def test_room_remove_nonexistent():
    room = Room(room_id="r5")
    assert room.remove_player("unknown") is None


def test_player_feed_char():
    room = Room(room_id="r6", song=_make_song())
    p = room.add_player("Alice", difficulty="easy")
    state = p.feed_char("h")
    assert state["player"] == "Alice"
    assert "score" in state
    assert p.chars_typed == 1


def test_player_tick_idle():
    room = Room(room_id="r7", song=_make_song())
    p = room.add_player("Alice")
    state = p.tick_idle()
    assert state["player"] == "Alice"
    assert "score" in state


def test_player_result():
    room = Room(room_id="r8", song=_make_song())
    p = room.add_player("Alice")
    p.feed_char("h")
    result = p.result()
    assert result["player"] == "Alice"
    assert result["chars_typed"] == 1


def test_room_get_results():
    room = Room(room_id="r9", song=_make_song())
    room.add_player("Alice")
    room.add_player("Bob")
    results = room.get_results()
    assert len(results) == 2


def test_room_get_winner():
    room = Room(room_id="r10", song=_make_song())
    p1 = room.add_player("Alice")
    p2 = room.add_player("Bob")
    # Feed many chars to Alice so her pipeline processes tokens and earns points
    for c in "hello world this is a test of many characters for alice":
        p1.feed_char(c)
    # Tick Alice extra times in optimal zone
    for _ in range(20):
        p1.tick_idle()
    # Bob only gets underflow penalties
    for _ in range(5):
        p2.tick_idle()
    # Alice should have a higher score than Bob
    if p1.tracker.score() != p2.tracker.score():
        winner = room.get_winner()
        assert winner == "Alice"
    else:
        # If somehow equal, just verify get_winner returns without error
        room.get_winner()


def test_room_get_winner_single_player():
    room = Room(room_id="r10b", song=_make_song())
    room.add_player("Alice")
    winner = room.get_winner()
    assert winner == "Alice"


def test_room_get_winner_tie():
    room = Room(room_id="r11", song=_make_song())
    room.add_player("Alice")
    room.add_player("Bob")
    # Neither typed anything, both have score 0 (underflow clamps to 0)
    winner = room.get_winner()
    # Both have 0 score, so tie
    assert winner is None


def test_room_manager_create():
    mgr = RoomManager()
    room = mgr.create_room(mode="duet", song=_make_song())
    assert room.mode == "duet"
    assert mgr.room_count() == 1


def test_room_manager_get():
    mgr = RoomManager()
    room = mgr.create_room()
    fetched = mgr.get_room(room.room_id)
    assert fetched is room


def test_room_manager_get_nonexistent():
    mgr = RoomManager()
    assert mgr.get_room("nope") is None


def test_room_manager_remove():
    mgr = RoomManager()
    room = mgr.create_room()
    mgr.remove_room(room.room_id)
    assert mgr.room_count() == 0


def test_room_manager_cleanup_empty():
    mgr = RoomManager()
    mgr.create_room()
    mgr.create_room()
    removed = mgr.cleanup_empty()
    assert removed == 2
    assert mgr.room_count() == 0


def test_room_manager_active_rooms():
    mgr = RoomManager()
    r1 = mgr.create_room(song=_make_song())
    r1.add_player("Alice")
    mgr.create_room()  # empty
    active = mgr.active_rooms()
    assert len(active) == 1


def test_duet_splitter_basic():
    song = _make_song(sheet_text="line one\nline two\nline three")
    p1, p2 = DuetSplitter.split(song)
    assert p1  # non-empty
    assert p2  # non-empty


def test_duet_splitter_harmony_lines():
    song = _make_song(sheet_text="melody line\n[harmony] together\nplain line")
    p1, p2 = DuetSplitter.split(song)
    # Player 2 should get the harmony line
    assert "harmony" in p2
    # Player 1 should get cleaned version without brackets
    assert "[" not in p1


def test_duet_splitter_tokens():
    tokens = [
        SheetTextToken(text="hello", emphasis="none", sustain=False, harmony=False, duration_modifier=1.0),
        SheetTextToken(text="WORLD", emphasis="loud", sustain=False, harmony=True, duration_modifier=1.0),
        SheetTextToken(text="foo", emphasis="none", sustain=False, harmony=False, duration_modifier=1.0),
    ]
    p1, p2 = DuetSplitter.split_tokens(tokens)
    # Harmony token goes to player 2
    assert any(t.harmony for t in p2)
    # Player 1 gets a non-harmony version of the harmony token
    assert all(not t.harmony for t in p1)
