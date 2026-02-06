/**
 * Audio player stub for Mavis mobile.
 *
 * In a full implementation, this would use expo-av or react-native-audio-api
 * to play audio received from the server. For Phase 3, audio synthesis is
 * handled server-side; this stub is a placeholder for future client-side
 * audio playback.
 */

export default class AudioPlayer {
  constructor() {
    this.isPlaying = false;
  }

  async play(audioData) {
    // Stub: server handles audio synthesis in Phase 3.
    // Future implementation would decode PCM and play via expo-av.
    this.isPlaying = true;
  }

  stop() {
    this.isPlaying = false;
  }
}
