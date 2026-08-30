// Talks to the FastAPI server. Nothing else in the UI knows about HTTP or
// WebSockets - the store calls these methods and that is the whole seam.
//
// Changes go over the WebSocket when it is open: no HTTP round-trip per
// slider step, and the server does not echo a change back to whoever made
// it, so a control being dragged is never fought by its own value. HTTP is
// the fallback for when the socket is down.

/**
 * Where the API lives.
 *
 * The server serves this page and the API on the same origin, so the answer
 * is "wherever the page came from" - no host, no port, nothing to keep in
 * sync. Whatever address you opened, from a phone or the kiosk, the API is
 * on it.
 *
 * Set window.KATANA_API_URL before this script loads to point somewhere
 * else, for a UI served separately from the API it talks to.
 */
function resolveBase() {
  const configured = window.KATANA_API_URL?.replace(/\/$/, "");
  if (configured) return configured;
  return window.location.origin;
}

const BASE = resolveBase();

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
let reconnectTimer = null;
let closedByUs = false;

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
    if (closedByUs) return;
    // Back off, but keep trying - the Pi may still be booting.
    const delay = Math.min(1000 * 2 ** reconnectAttempts, 10000);
    reconnectAttempts += 1;
    reconnectTimer = setTimeout(openSocket, delay);
  };

  ws.onerror = () => ws.close();
}

function socketReady() {
  return socket !== null && socket.readyState === WebSocket.OPEN;
}

export const transport = {
  connect() {
    closedByUs = false;
    openSocket();
  },

  disconnect() {
    closedByUs = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    socket?.close();
    socket = null;
  },

  /** Fire-and-forget parameter write. */
  send(key, value) {
    const wire = toWire(value);
    if (socketReady()) {
      socket.send(JSON.stringify({ type: "set", name: key, value: wire }));
      return;
    }
    void request(`/api/parameter/${key}`, {
      method: "PUT",
      body: JSON.stringify({ value: wire }),
    }).catch((error) => console.error("[katana]", error));
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
    if (socketReady()) {
      socket.send(JSON.stringify({ type: "channel", name: id }));
      return;
    }
    void request(`/api/channel/${id}`, { method: "POST" }).catch((error) =>
      console.error("[katana]", error),
    );
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

  /** Everything the amp currently reports. */
  async state() {
    return request("/api/state");
  },

  /** Full state re-read. The amp never reports physical knob turns. */
  async resync() {
    return request("/api/refresh", { method: "POST" });
  },

  /** Channel list and the names of the stored patches. */
  async channels() {
    return request("/api/channels");
  },

  /** .tsl files on the server and the patches inside them. */
  async patchFiles() {
    return request("/api/tsl");
  },

  async loadPatchFile(file, index) {
    return request(`/api/tsl/${encodeURIComponent(file)}/${index}`, { method: "POST" });
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
