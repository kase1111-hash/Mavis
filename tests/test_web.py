"""Tests for web.server -- FastAPI REST endpoints, WebSocket gameplay, auth, and licensing."""

import json

import pytest
from fastapi.testclient import TestClient

from web.server import app


@pytest.fixture
def client():
    """Provide a TestClient for the FastAPI app."""
    return TestClient(app)


# --- Health Check ---

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# --- Song Endpoints ---

def test_get_songs(client):
    resp = client.get("/api/songs")
    assert resp.status_code == 200
    songs = resp.json()
    assert isinstance(songs, list)
    assert len(songs) > 0
    assert "title" in songs[0]
    assert "song_id" in songs[0]


def test_get_songs_filter_difficulty(client):
    resp = client.get("/api/songs?difficulty=easy")
    assert resp.status_code == 200
    songs = resp.json()
    assert all(s["difficulty"] == "easy" for s in songs)


def test_get_song_by_id(client):
    resp = client.get("/api/songs/twinkle")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("song_id") == "twinkle" or "error" not in data


def test_get_song_not_found(client):
    resp = client.get("/api/songs/nonexistent_song_xyz")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


# --- Leaderboard Endpoints ---

def test_get_leaderboard(client):
    resp = client.get("/api/leaderboard/twinkle")
    assert resp.status_code == 200
    data = resp.json()
    assert "song_id" in data
    assert "scores" in data


def test_submit_score(client):
    resp = client.post("/api/leaderboard/twinkle", json={
        "player_name": "WebTester",
        "score": 500,
        "grade": "B",
        "difficulty": "easy",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "rank" in data


# --- Auth Endpoints ---

def test_register_and_login(client):
    import uuid
    username = f"testuser_{uuid.uuid4().hex[:6]}"
    # Register
    resp = client.post("/auth/register", json={
        "username": username,
        "password": "testpass",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["username"] == username

    # Login
    resp = client.post("/auth/login", json={
        "username": username,
        "password": "testpass",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data


def test_profile_with_auth_header(client):
    """Test that the Authorization header works for authenticated endpoints."""
    import uuid
    username = f"headeruser_{uuid.uuid4().hex[:6]}"
    resp = client.post("/auth/register", json={
        "username": username,
        "password": "testpass",
    })
    token = resp.json()["token"]

    # Access profile via Authorization header (preferred)
    resp = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == username
    assert "error" not in data


def test_register_short_username(client):
    resp = client.post("/auth/register", json={
        "username": "a",
        "password": "testpass",
    })
    data = resp.json()
    assert "error" in data


def test_register_short_password(client):
    resp = client.post("/auth/register", json={
        "username": "validname",
        "password": "ab",
    })
    data = resp.json()
    assert "error" in data


def test_login_invalid_credentials(client):
    resp = client.post("/auth/login", json={
        "username": "nonexistent_user_xyz",
        "password": "wrong",
    })
    data = resp.json()
    assert "error" in data


def test_profile_invalid_token(client):
    resp = client.get("/api/profile?token=invalid_token")
    data = resp.json()
    assert "error" in data


# --- License Endpoints ---

def test_get_license_tiers(client):
    resp = client.get("/api/license/tiers")
    assert resp.status_code == 200
    tiers = resp.json()
    assert isinstance(tiers, list)
    assert len(tiers) == 3


def test_get_current_license(client):
    resp = client.get("/api/license/current")
    assert resp.status_code == 200
    data = resp.json()
    assert "tier" in data


def test_activate_invalid_license(client):
    resp = client.post("/api/license/activate", json={"key": "bad-key"})
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


def test_deactivate_license(client):
    resp = client.post("/api/license/deactivate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "free"


# --- Researcher API Endpoints ---

def test_researcher_register_key(client):
    resp = client.post("/api/v1/register", json={"owner": "Dr. Test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "api_key" in data
    assert data["api_key"].startswith("mavis_")


def test_researcher_performances_no_key(client):
    resp = client.get("/api/v1/performances")
    data = resp.json()
    assert "error" in data


def test_researcher_statistics_no_key(client):
    resp = client.get("/api/v1/statistics")
    data = resp.json()
    assert "error" in data


# --- Room Endpoints ---

def test_create_and_get_room(client):
    resp = client.post("/api/rooms", json={"mode": "competitive"})
    assert resp.status_code == 200
    data = resp.json()
    assert "room_id" in data

    room_id = data["room_id"]
    resp = client.get(f"/api/rooms/{room_id}")
    assert resp.status_code == 200
    room = resp.json()
    assert room["mode"] == "competitive"


def test_get_room_not_found(client):
    resp = client.get("/api/rooms/nonexistent")
    data = resp.json()
    assert "error" in data


# --- Community Song Endpoints ---

def test_browse_community(client):
    resp = client.get("/api/songs/community")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# --- WebSocket Gameplay ---

def test_websocket_play_basic(client):
    with client.websocket_connect("/ws/play") as ws:
        ws.send_json({"type": "start", "difficulty": "easy", "voice": "default"})
        resp = ws.receive_json()
        assert resp["type"] == "started"
        assert "session_id" in resp

        # Send a key
        ws.send_json({"type": "key", "char": "a", "shift": False, "ctrl": False})
        resp = ws.receive_json()
        assert resp["type"] == "state"
        assert "score" in resp

        # Send a tick
        ws.send_json({"type": "tick"})
        resp = ws.receive_json()
        assert resp["type"] == "state"

        # Stop
        ws.send_json({"type": "stop"})
        resp = ws.receive_json()
        assert resp["type"] == "result"
        assert "score" in resp


def test_websocket_play_with_song(client):
    with client.websocket_connect("/ws/play") as ws:
        ws.send_json({
            "type": "start",
            "difficulty": "easy",
            "song_id": "twinkle",
        })
        resp = ws.receive_json()
        assert resp["type"] == "started"
        assert resp["song"] is not None
        assert resp["song"]["title"] == "Twinkle Twinkle Little Star"

        ws.send_json({"type": "stop"})
        resp = ws.receive_json()
        assert resp["type"] == "result"


def test_websocket_invalid_json(client):
    with client.websocket_connect("/ws/play") as ws:
        ws.send_text("not valid json{{{")
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "Invalid JSON" in resp["message"]


def test_websocket_message_too_large(client):
    with client.websocket_connect("/ws/play") as ws:
        ws.send_text("x" * 5000)
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "too large" in resp["message"].lower()
