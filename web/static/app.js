// Mavis Web Client

let ws = null;
let typedChars = [];
let gameActive = false;
let tickInterval = null;

// --- Screen management ---

function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
}

function showMenu() {
    stopGame();
    showScreen('menu-screen');
}

function showSettings() {
    showScreen('settings-screen');
}

// --- Song Browser ---

async function showSongBrowser() {
    showScreen('song-browser');
    await loadSongs(null);
}

async function loadSongs(difficulty) {
    let url = '/api/songs';
    if (difficulty) url += '?difficulty=' + difficulty;
    const resp = await fetch(url);
    const songs = await resp.json();
    renderSongList(songs);
}

function filterSongs(difficulty) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    loadSongs(difficulty);
}

function renderSongList(songs) {
    const list = document.getElementById('song-list');
    list.innerHTML = '';
    songs.forEach(song => {
        const card = document.createElement('div');
        card.className = 'song-card';
        card.onclick = () => startGame(song.song_id, song.title, song.sheet_text);
        card.innerHTML = `
            <div>
                <span class="song-title">${song.title}</span>
                <span class="song-meta">${song.bpm} bpm, ${song.token_count} tokens</span>
            </div>
            <span class="diff-${song.difficulty}">${song.difficulty.toUpperCase()}</span>
        `;
        list.appendChild(card);
    });
}

// --- Gameplay ---

function startGame(songId, title, sheetText) {
    const difficulty = document.getElementById('difficulty-select').value;
    const voice = document.getElementById('voice-select').value;

    showScreen('game-screen');
    document.getElementById('game-title').textContent = title;
    document.getElementById('sheet-text-display').textContent = sheetText;
    document.getElementById('typed-text').textContent = '';
    document.getElementById('game-score').textContent = '0';
    document.getElementById('game-grade').textContent = 'F';
    typedChars = [];
    gameActive = true;

    // Connect WebSocket
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws/play`);

    ws.onopen = () => {
        ws.send(JSON.stringify({
            type: 'start',
            song_id: songId,
            difficulty: difficulty,
            voice: voice,
        }));
    };

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'state') {
            updateGameDisplay(msg);
        } else if (msg.type === 'result') {
            showResults(msg);
        }
    };

    ws.onclose = () => {
        gameActive = false;
    };

    // Start idle tick interval (~30fps)
    tickInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN && gameActive) {
            ws.send(JSON.stringify({ type: 'tick' }));
        }
    }, 33);

    // Capture keyboard
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
}

function stopGame() {
    gameActive = false;
    if (tickInterval) {
        clearInterval(tickInterval);
        tickInterval = null;
    }
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'stop' }));
        ws.close();
    }
    ws = null;
    document.removeEventListener('keydown', handleKeyDown);
    document.removeEventListener('keyup', handleKeyUp);
}

function handleKeyDown(e) {
    if (!gameActive) return;

    // Esc to stop
    if (e.key === 'Escape') {
        stopGame();
        showResults({
            score: parseInt(document.getElementById('game-score').textContent),
            grade: document.getElementById('game-grade').textContent,
            phonemes_played: 0,
            chars_typed: typedChars.length,
        });
        return;
    }

    // Ignore modifier-only keys
    if (['Shift', 'Control', 'Alt', 'Meta', 'Tab'].includes(e.key)) return;

    e.preventDefault();

    let char = e.key;
    if (char.length > 1) return; // ignore special keys like F1, etc.

    const shift = e.shiftKey;
    const ctrl = e.ctrlKey;

    typedChars.push(char);
    document.getElementById('typed-text').textContent = typedChars.slice(-60).join('');

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'key',
            char: char,
            shift: shift,
            ctrl: ctrl,
        }));
    }
}

function handleKeyUp(e) {
    // placeholder for future sustain detection
}

function updateGameDisplay(state) {
    // Input buffer
    const inputPct = Math.round(state.input_level * 100);
    document.getElementById('input-bar').style.width = inputPct + '%';
    document.getElementById('input-pct').textContent = inputPct + '%';

    // Output buffer
    const outputPct = Math.round(state.output_level * 100);
    const outputBar = document.getElementById('output-bar');
    outputBar.style.width = outputPct + '%';
    outputBar.className = 'bar-fill';
    if (state.output_status === 'overflow') outputBar.classList.add('overflow');
    else if (state.output_status === 'underflow') outputBar.classList.add('underflow');
    document.getElementById('output-pct').textContent = outputPct + '%';

    const statusBadge = document.getElementById('output-status');
    statusBadge.textContent = state.output_status;
    statusBadge.className = 'status-badge status-' + state.output_status;

    // Phoneme and tokens
    document.getElementById('current-phoneme').textContent = state.last_phoneme || '-';
    document.getElementById('current-tokens').textContent =
        state.last_tokens && state.last_tokens.length > 0
            ? state.last_tokens.slice(0, 5).join(' ')
            : '-';

    // Score
    document.getElementById('game-score').textContent = state.score;
    document.getElementById('game-grade').textContent = state.grade;
}

function showResults(result) {
    gameActive = false;
    showScreen('results-screen');

    const content = document.getElementById('results-content');
    content.innerHTML = `
        <div>Final Score: <strong>${result.score}</strong></div>
        <div>Grade: <strong>${result.grade}</strong></div>
        <div>Phonemes Played: ${result.phonemes_played || 0}</div>
        <div>Characters Typed: ${result.chars_typed || typedChars.length}</div>
    `;
}

// --- Leaderboard ---

async function showLeaderboard() {
    showScreen('leaderboard-screen');
    const resp = await fetch('/api/songs');
    const songs = await resp.json();

    const content = document.getElementById('leaderboard-content');
    content.innerHTML = '<p style="color: var(--text-dim)">Loading...</p>';

    let html = '';
    for (const song of songs) {
        const lbResp = await fetch(`/api/leaderboard/${song.song_id}?limit=5`);
        const lb = await lbResp.json();
        if (lb.scores && lb.scores.length > 0) {
            html += `<div class="lb-song"><h3>${song.title}</h3>`;
            lb.scores.forEach((entry, i) => {
                html += `<div class="lb-entry">
                    <span class="lb-rank">${i + 1}.</span>
                    <span class="lb-name">${entry.player_name || '???'}</span>
                    <span class="lb-score">${entry.score}</span>
                    <span class="lb-grade">[${entry.grade}]</span>
                </div>`;
            });
            html += '</div>';
        }
    }

    if (!html) {
        html = '<p style="color: var(--text-dim)">(no scores recorded yet)</p>';
    }
    content.innerHTML = html;
}

// --- Multiplayer ---

let mpWs = null;

async function showMultiplayer() {
    showScreen('multiplayer-screen');
    // Load songs for the song selector
    const resp = await fetch('/api/songs');
    const songs = await resp.json();
    const select = document.getElementById('mp-song');
    select.innerHTML = '';
    songs.forEach(song => {
        const opt = document.createElement('option');
        opt.value = song.song_id;
        opt.textContent = `${song.title} (${song.difficulty})`;
        select.appendChild(opt);
    });
    document.getElementById('mp-status').textContent = '';
}

async function createRoom() {
    const mode = document.getElementById('mp-mode').value;
    const songId = document.getElementById('mp-song').value;
    const resp = await fetch('/api/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: mode, song_id: songId }),
    });
    const data = await resp.json();
    document.getElementById('mp-status').innerHTML =
        `Room created! Code: <strong>${data.room_id}</strong><br>Share this code with a friend.` +
        `<br><button onclick="joinRoomById('${data.room_id}')">Join Your Room</button>`;
}

function joinRoom() {
    const code = document.getElementById('room-code').value.trim();
    if (code) joinRoomById(code);
}

function joinRoomById(roomId) {
    const difficulty = document.getElementById('difficulty-select').value;
    const voice = document.getElementById('voice-select').value;
    const playerName = document.getElementById('player-name').value || 'Player';

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    mpWs = new WebSocket(`${protocol}//${location.host}/ws/room/${roomId}`);

    mpWs.onopen = () => {
        mpWs.send(JSON.stringify({
            type: 'join',
            player_name: playerName,
            difficulty: difficulty,
            voice: voice,
        }));
    };

    mpWs.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        const status = document.getElementById('mp-status');

        if (msg.type === 'player_joined') {
            status.innerHTML += `<br>${msg.player_name} joined (${msg.player_count}/2 players)`;
            if (msg.player_count === 2 && msg.song) {
                status.innerHTML += `<br>Both players ready! Starting...`;
                // Could auto-start game here
            }
        } else if (msg.type === 'player_left') {
            status.innerHTML += `<br>${msg.player_name} left`;
        } else if (msg.type === 'error') {
            status.innerHTML += `<br>Error: ${msg.message}`;
        } else if (msg.type === 'opponent_state') {
            status.innerHTML = `Opponent ${msg.player}: Score ${msg.score} [${msg.grade}]`;
        }
    };

    mpWs.onclose = () => {
        document.getElementById('mp-status').innerHTML += '<br>Disconnected.';
    };
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    showScreen('menu-screen');
});
