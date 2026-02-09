"""Tests for web.server -- FastAPI REST endpoints and WebSocket gameplay."""

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
