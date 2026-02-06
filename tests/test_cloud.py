"""Tests for mavis.cloud -- user accounts, auth, and sync."""

import os
import tempfile

from mavis.cloud import (
    SyncPayload,
    UserStore,
    check_password,
    generate_token,
    hash_password,
    verify_token,
)


def test_hash_and_check_password():
    h = hash_password("secret123")
    assert check_password("secret123", h)
    assert not check_password("wrong", h)


def test_hash_password_unique_salts():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # Different salts
    assert check_password("same", h1)
    assert check_password("same", h2)


def test_generate_and_verify_token():
    token = generate_token("user123", secret="test-secret")
    uid = verify_token(token, secret="test-secret")
    assert uid == "user123"


def test_verify_token_wrong_secret():
    token = generate_token("user123", secret="correct")
    uid = verify_token(token, secret="wrong")
    assert uid is None


def test_verify_token_expired():
    token = generate_token("user123", ttl_hours=0)
    uid = verify_token(token)
    assert uid is None


def test_verify_token_malformed():
    assert verify_token("garbage") is None
    assert verify_token("") is None
    assert verify_token("a:b:c:d") is None


def test_user_store_register():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        profile = store.register("alice", "pass123")
        assert profile is not None
        assert profile.username == "alice"
        assert profile.user_id
        assert store.user_count() == 1
    finally:
        os.unlink(path)


def test_user_store_duplicate_username():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        store.register("alice", "pass1")
        dupe = store.register("Alice", "pass2")  # case insensitive
        assert dupe is None
        assert store.user_count() == 1
    finally:
        os.unlink(path)


def test_user_store_authenticate():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        store.register("bob", "secret")
        profile = store.authenticate("bob", "secret")
        assert profile is not None
        assert profile.username == "bob"
    finally:
        os.unlink(path)


def test_user_store_authenticate_wrong_password():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        store.register("bob", "secret")
        assert store.authenticate("bob", "wrong") is None
    finally:
        os.unlink(path)


def test_user_store_authenticate_unknown_user():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        assert store.authenticate("nobody", "pass") is None
    finally:
        os.unlink(path)


def test_user_store_get_user():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        p = store.register("carol", "pass")
        fetched = store.get_user(p.user_id)
        assert fetched is not None
        assert fetched.username == "carol"
    finally:
        os.unlink(path)


def test_user_store_update_user():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        p = store.register("dave", "pass")
        p.voice_preference = "soprano"
        store.update_user(p)
        fetched = store.get_user(p.user_id)
        assert fetched.voice_preference == "soprano"
    finally:
        os.unlink(path)


def test_user_store_sync_preferences():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        p = store.register("eve", "pass")
        payload = SyncPayload(
            user_id=p.user_id,
            voice_preference="bass",
            difficulty_preference="hard",
        )
        updated = store.sync(payload)
        assert updated is not None
        assert updated.voice_preference == "bass"
        assert updated.difficulty_preference == "hard"
    finally:
        os.unlink(path)


def test_user_store_sync_tutorial_keeps_better_grade():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        p = store.register("frank", "pass")
        # First sync: set grade A for lesson 1
        store.sync(SyncPayload(user_id=p.user_id, tutorial_progress={1: "A"}))
        # Second sync: try to downgrade to C
        updated = store.sync(SyncPayload(user_id=p.user_id, tutorial_progress={1: "C"}))
        assert updated.tutorial_progress[1] == "A"
    finally:
        os.unlink(path)


def test_user_store_sync_personal_bests():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        p = store.register("grace", "pass")
        store.sync(SyncPayload(
            user_id=p.user_id,
            personal_bests={"twinkle": {"score": 100, "grade": "B"}},
        ))
        updated = store.sync(SyncPayload(
            user_id=p.user_id,
            personal_bests={"twinkle": {"score": 200, "grade": "A"}},
        ))
        assert updated.personal_bests["twinkle"]["score"] == 200
    finally:
        os.unlink(path)


def test_user_store_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store1 = UserStore(path=path)
        store1.register("heidi", "pass")
        # Load from disk in a new instance
        store2 = UserStore(path=path)
        assert store2.user_count() == 1
        assert store2.authenticate("heidi", "pass") is not None
    finally:
        os.unlink(path)


def test_user_profile_to_dict_excludes_password():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = UserStore(path=path)
        p = store.register("ivan", "secret")
        d = p.to_dict()
        assert "password_hash" not in d
        assert d["username"] == "ivan"
    finally:
        os.unlink(path)
