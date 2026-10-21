// Talks to the FastAPI server. Nothing else in the UI knows about HTTP or
// WebSockets - the store calls these methods and that is the whole seam.
//
// Live changes (knobs, channels) go over the WebSocket: no HTTP round-trip
// per slider step, and the server does not echo a change back to whoever
// made it, so a control being dragged is never fought by its own value.
// One-off actions (save, resync, wah gestures) are plain HTTP.

// The server serves this page and the API together, so the API is wherever
// the page came from.
export const BASE = window.location.origin;

/** The amp stores booleans as 0/1. */
function toWire(value) {
  return typeof value === "boolean" ? (value ? 1 : 0) : value;
}

async function request(path, init) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    throw new Error(`${path}: ${detail}`);
  }
  return response.json();
}

let socket = null;
let messageListeners = [];
let stateListeners = [];
let reconnectAttempts = 0;

function announce(state) {
  stateListeners.forEach((fn) => fn(state));
}

function openSocket() {
  if (socket && socket.readyState <= WebSocket.OPEN) return;

  announce("connecting");
  const ws = new WebSocket(`${BASE.replace(/^http/, "ws")}/ws`);
  socket = ws;

  ws.onopen = () => {
    reconnectAttempts = 0;
    announce("open");
  };

  ws.onmessage = (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch {
      return;
    }
    messageListeners.forEach((fn) => fn(message));
  };

  ws.onclose = () => {
    socket = null;
    announce("closed");
    // Back off, but keep trying - the Pi may still be booting.
    const delay = Math.min(1000 * 2 ** reconnectAttempts, 10000);
    reconnectAttempts += 1;
    setTimeout(openSocket, delay);
  };

  ws.onerror = () => ws.close();
}

/** Send one message over the socket. While it is reconnecting there is
 *  nowhere to send it, and the change is dropped. */
function sendMessage(message) {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
}

function write(key, value) {
  sendMessage({ type: "set", name: key, value: toWire(value) });
}

// At most one write per parameter every THROTTLE_MS, and the last value
// always goes out. The amp takes ~40 writes/s; faster than that, writes
// queue on the server and the sound lags behind the finger.
const THROTTLE_MS = 40;
const waiting = new Map(); // key -> newest value not sent yet
const timers = new Map();  // key -> the running throttle timer

export const transport = {
  connect() {
    openSocket();
  },

  /** Fire-and-forget parameter write, throttled per parameter. */
  send(key, value) {
    if (timers.has(key)) {
      // Sent one recently - just remember the newest.
      waiting.set(key, value);
      return;
    }
    // First change: send right away, no delay.
    write(key, value);
    const tick = () => {
      if (waiting.has(key)) {
        // Something changed meanwhile: send the latest.
        write(key, waiting.get(key));
        waiting.delete(key);
        timers.set(key, setTimeout(tick, THROTTLE_MS));
      } else {
        // Quiet - the next change goes out instantly again.
        timers.delete(key);
      }
    };
    timers.set(key, setTimeout(tick, THROTTLE_MS));
  },

  /** Footswitch-style CC message. */
  sendCC(cc, value) {
    void request(`/api/cc/${cc}`, {
      method: "POST",
      body: JSON.stringify({ value }),
    }).catch((error) => console.error("[katana]", error));
  },

  /** Switch tone-setting channel. The amp reloads, so a whole new state follows. */
  selectChannel(id) {
    sendMessage({ type: "channel", name: id });
  },

  /** Copy the live sound into a stored channel. Overwrites it permanently. */
  async saveToPatch(number) {
    return request(`/api/patch/${number}`, { method: "POST" });
  },

  /** Server-side treadle sweep - one request, never stepped from the browser. */
  sweepWah(from, to, ms) {
    const steps = 25;
    void request("/api/wah/sweep", {
      method: "POST",
      body: JSON.stringify({
        start: from,
        end: to,
        steps,
        delay: Math.max(ms / steps / 1000, 0.01),
      }),
    }).catch((error) => console.error("[katana]", error));
  },

  /** Repeating wah gesture - N sweeps of low..high, `seconds` each.
   *  Server-side for the same reason as sweepWah: hundreds of MIDI writes. */
  rockWah({ intervals, low, high, seconds, bounce }) {
    return request("/api/wah/rock", {
      method: "POST",
      body: JSON.stringify({ intervals, low, high, seconds, bounce }),
    });
  },

  /** Full state re-read. The amp never reports physical knob turns. */
  async resync() {
    return request("/api/refresh", { method: "POST" });
  },

  /** Channel list and the names of the stored patches. */
  async channels() {
    return request("/api/channels");
  },

  onMessage(fn) {
    messageListeners.push(fn);
    return () => {
      messageListeners = messageListeners.filter((l) => l !== fn);
    };
  },

  onConnectionChange(fn) {
    stateListeners.push(fn);
    return () => {
      stateListeners = stateListeners.filter((l) => l !== fn);
    };
  },
};
