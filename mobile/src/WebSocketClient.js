/**
 * WebSocket client wrapper for Mavis mobile.
 *
 * Handles connection lifecycle, JSON serialization, and reconnection.
 */

export default class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.onOpen = null;
    this.onMessage = null;
    this.onClose = null;
    this.onError = null;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      if (this.onOpen) this.onOpen();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (this.onMessage) this.onMessage(msg);
      } catch (e) {
        // Ignore non-JSON messages
      }
    };

    this.ws.onclose = (event) => {
      if (this.onClose) this.onClose(event.code, event.reason);
    };

    this.ws.onerror = (error) => {
      if (this.onError) this.onError(error);
    };
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  close() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}
