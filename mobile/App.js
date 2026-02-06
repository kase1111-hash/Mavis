/**
 * Mavis Mobile - React Native thin client.
 *
 * Connects to the Mavis backend via WebSocket and renders the game UI.
 * Touch gestures map to keyboard equivalents:
 *   - Tap key: normal keypress
 *   - Long press: sustain (...)
 *   - Swipe up: Shift (CAPS) - loud emphasis
 *   - Swipe down: underscore wrapper - soft emphasis
 *   - Two-finger tap: Ctrl (brackets) - harmony
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Alert,
} from 'react-native';

import WebSocketClient from './src/WebSocketClient';
import BufferDisplay from './src/BufferDisplay';
import SheetTextView from './src/SheetTextView';
import AudioPlayer from './src/AudioPlayer';

const DEFAULT_SERVER = 'ws://localhost:8000/ws/play';

export default function App() {
  const [screen, setScreen] = useState('menu'); // menu | settings | songs | game | results
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER);
  const [songs, setSongs] = useState([]);
  const [currentSong, setCurrentSong] = useState(null);
  const [gameState, setGameState] = useState(null);
  const [results, setResults] = useState(null);
  const [difficulty, setDifficulty] = useState('medium');
  const [voice, setVoice] = useState('default');
  const wsRef = useRef(null);

  const httpBase = serverUrl.replace('ws://', 'http://').replace('wss://', 'https://').replace('/ws/play', '');

  const loadSongs = useCallback(async () => {
    try {
      const resp = await fetch(`${httpBase}/api/songs`);
      const data = await resp.json();
      setSongs(data);
      setScreen('songs');
    } catch (err) {
      Alert.alert('Connection Error', `Cannot reach server at ${httpBase}`);
    }
  }, [httpBase]);

  const startGame = useCallback((song) => {
    setCurrentSong(song);
    setGameState(null);
    setScreen('game');

    const ws = new WebSocketClient(serverUrl);
    wsRef.current = ws;

    ws.onOpen = () => {
      ws.send({
        type: 'start',
        song_id: song.song_id,
        difficulty: difficulty,
        voice: voice,
      });
    };

    ws.onMessage = (msg) => {
      if (msg.type === 'state') {
        setGameState(msg);
      } else if (msg.type === 'result') {
        setResults(msg);
        setScreen('results');
      }
    };

    ws.onClose = () => {
      // Connection closed
    };

    ws.connect();
  }, [serverUrl, difficulty, voice]);

  const sendKey = useCallback((char, shift = false, ctrl = false) => {
    if (wsRef.current) {
      wsRef.current.send({
        type: 'key',
        char: char,
        shift: shift,
        ctrl: ctrl,
      });
    }
  }, []);

  const stopGame = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.send({ type: 'stop' });
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Idle tick timer for game screen
  useEffect(() => {
    if (screen !== 'game' || !wsRef.current) return;
    const interval = setInterval(() => {
      if (wsRef.current) {
        wsRef.current.send({ type: 'tick' });
      }
    }, 33);
    return () => clearInterval(interval);
  }, [screen]);

  // --- Screen renderers ---

  if (screen === 'menu') {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Mavis</Text>
        <Text style={styles.subtitle}>Turn typing into singing</Text>
        <TouchableOpacity style={styles.button} onPress={loadSongs}>
          <Text style={styles.buttonText}>Play a Song</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.button} onPress={() => setScreen('settings')}>
          <Text style={styles.buttonText}>Settings</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (screen === 'settings') {
    return (
      <View style={styles.container}>
        <Text style={styles.heading}>Settings</Text>
        <Text style={styles.label}>Server URL:</Text>
        <TextInput
          style={styles.input}
          value={serverUrl}
          onChangeText={setServerUrl}
          autoCapitalize="none"
        />
        <Text style={styles.label}>Difficulty: {difficulty}</Text>
        <View style={styles.row}>
          {['easy', 'medium', 'hard', 'expert'].map((d) => (
            <TouchableOpacity
              key={d}
              style={[styles.chip, difficulty === d && styles.chipActive]}
              onPress={() => setDifficulty(d)}
            >
              <Text style={styles.chipText}>{d.toUpperCase()}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <Text style={styles.label}>Voice: {voice}</Text>
        <View style={styles.row}>
          {['default', 'alto', 'soprano', 'bass', 'whisper', 'robot'].map((v) => (
            <TouchableOpacity
              key={v}
              style={[styles.chip, voice === v && styles.chipActive]}
              onPress={() => setVoice(v)}
            >
              <Text style={styles.chipText}>{v}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <TouchableOpacity style={styles.backBtn} onPress={() => setScreen('menu')}>
          <Text style={styles.buttonText}>Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (screen === 'songs') {
    return (
      <View style={styles.container}>
        <Text style={styles.heading}>Select a Song</Text>
        <ScrollView style={styles.songList}>
          {songs.map((song) => (
            <TouchableOpacity
              key={song.song_id}
              style={styles.songCard}
              onPress={() => startGame(song)}
            >
              <Text style={styles.songTitle}>{song.title}</Text>
              <Text style={styles.songMeta}>
                {song.bpm} bpm | {song.difficulty} | {song.token_count} tokens
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        <TouchableOpacity style={styles.backBtn} onPress={() => setScreen('menu')}>
          <Text style={styles.buttonText}>Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (screen === 'game') {
    return (
      <View style={styles.container}>
        <Text style={styles.heading}>{currentSong?.title}</Text>
        {gameState && (
          <>
            <BufferDisplay
              inputLevel={gameState.input_level}
              outputLevel={gameState.output_level}
              outputStatus={gameState.output_status}
            />
            <View style={styles.statsRow}>
              <Text style={styles.stat}>Score: {gameState.score}</Text>
              <Text style={styles.stat}>Grade: {gameState.grade}</Text>
            </View>
          </>
        )}
        <SheetTextView text={currentSong?.sheet_text || ''} />
        <TextInput
          style={styles.gameInput}
          placeholder="Type here to sing..."
          placeholderTextColor="#666"
          autoFocus
          onChangeText={(text) => {
            if (text.length > 0) {
              const char = text[text.length - 1];
              sendKey(char, char === char.toUpperCase() && char !== char.toLowerCase());
            }
          }}
        />
        <TouchableOpacity style={styles.stopBtn} onPress={stopGame}>
          <Text style={styles.buttonText}>End Performance</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (screen === 'results') {
    return (
      <View style={styles.container}>
        <Text style={styles.heading}>Performance Complete!</Text>
        {results && (
          <View style={styles.resultsBox}>
            <Text style={styles.resultText}>Score: {results.score}</Text>
            <Text style={styles.resultText}>Grade: {results.grade}</Text>
            <Text style={styles.resultText}>Phonemes: {results.phonemes_played || 0}</Text>
            <Text style={styles.resultText}>Characters: {results.chars_typed || 0}</Text>
          </View>
        )}
        <TouchableOpacity style={styles.button} onPress={loadSongs}>
          <Text style={styles.buttonText}>Play Again</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.backBtn} onPress={() => setScreen('menu')}>
          <Text style={styles.buttonText}>Main Menu</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
    padding: 24,
    paddingTop: 60,
  },
  title: {
    fontSize: 48,
    color: '#22d3ee',
    fontFamily: 'monospace',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
    marginBottom: 32,
  },
  heading: {
    fontSize: 24,
    color: '#22d3ee',
    fontFamily: 'monospace',
    marginBottom: 16,
  },
  button: {
    backgroundColor: '#0f3460',
    borderColor: '#e94560',
    borderWidth: 1,
    borderRadius: 4,
    padding: 14,
    marginBottom: 10,
    alignItems: 'center',
  },
  backBtn: {
    backgroundColor: 'transparent',
    borderColor: '#888',
    borderWidth: 1,
    borderRadius: 4,
    padding: 14,
    marginTop: 16,
    alignItems: 'center',
  },
  stopBtn: {
    backgroundColor: '#e94560',
    borderRadius: 4,
    padding: 14,
    marginTop: 16,
    alignItems: 'center',
  },
  buttonText: {
    color: '#eee',
    fontSize: 16,
    fontFamily: 'monospace',
  },
  label: {
    color: '#eee',
    fontSize: 14,
    fontFamily: 'monospace',
    marginTop: 12,
    marginBottom: 4,
  },
  input: {
    backgroundColor: '#16213e',
    color: '#eee',
    borderColor: '#0f3460',
    borderWidth: 1,
    borderRadius: 4,
    padding: 10,
    fontFamily: 'monospace',
    fontSize: 14,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 8,
  },
  chip: {
    backgroundColor: '#0f3460',
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  chipActive: {
    backgroundColor: '#e94560',
  },
  chipText: {
    color: '#eee',
    fontSize: 12,
    fontFamily: 'monospace',
  },
  songList: {
    flex: 1,
  },
  songCard: {
    backgroundColor: '#16213e',
    borderColor: '#0f3460',
    borderWidth: 1,
    borderRadius: 4,
    padding: 12,
    marginBottom: 8,
  },
  songTitle: {
    color: '#eee',
    fontSize: 16,
    fontWeight: 'bold',
    fontFamily: 'monospace',
  },
  songMeta: {
    color: '#888',
    fontSize: 12,
    fontFamily: 'monospace',
    marginTop: 4,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  stat: {
    color: '#22d3ee',
    fontSize: 16,
    fontFamily: 'monospace',
    fontWeight: 'bold',
  },
  gameInput: {
    backgroundColor: '#16213e',
    color: '#eee',
    borderColor: '#0f3460',
    borderWidth: 1,
    borderRadius: 4,
    padding: 12,
    fontFamily: 'monospace',
    fontSize: 16,
    marginTop: 12,
  },
  resultsBox: {
    backgroundColor: '#16213e',
    borderRadius: 4,
    padding: 16,
    marginBottom: 16,
  },
  resultText: {
    color: '#eee',
    fontSize: 18,
    fontFamily: 'monospace',
    lineHeight: 32,
  },
});
