// Talks to the FastAPI server. Nothing else in the UI knows about HTTP or
// WebSockets - the store calls these methods and that is the whole seam.
//
// Changes go over the WebSocket when it is open: no HTTP round-trip per
// slider step, and the server does not echo a change back to whoever made
// it, so a control being dragged is never fought by its own value. HTTP is
// the fallback for when the socket is down.

export type ParamValue = number | boolean;

export type ServerMessage =
  | { type: "state"; values: Record<string, number> }
  | { type: "parameter"; name: string; value: number }
  | { type: "channel"; channel: string; values: Record<string, number> }
  | { type: "patch"; name: string; values: Record<string, number> }
  | { type: "patches"; names: Record<string, string> }
  | { type: "error"; detail: string };

export type ConnectionState = "connecting" | "open" | "closed";

/** Port the FastAPI server listens on. */
const API_PORT = "8000";

/**
 * Where the API lives.
 *
 * The page is served by Vite on :8080 but the API is a separate process on
 * :8000, so the origin alone is wrong. Deriving the host from the address
 * the page was actually loaded from is what makes a phone work: opening
 * http://192.168.1.124:8080 talks to http://192.168.1.124:8000, while
 * localhost keeps talking to localhost. A hardcoded "localhost" would mean
 * the phone itself, which is why it used to sit there disconnected.
 *
 * Set VITE_API_URL to override (e.g. the amp Pi's fixed address).
 */
function resolveBase(): string {
  const configured = (import.meta.env["VITE_API_URL"] as string | undefined)?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window === "undefined") return `http://localhost:${API_PORT}`; // SSR
  const { protocol, hostname } = window.location;
  return `${protocol}//${hostname}:${API_PORT}`;
}

const BASE = resolveBase();

/** The amp stores booleans as 0/1. */
function toWire(value: ParamValue): number {
  return typeof value === "boolean" ? (value ? 1 : 0) : value;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    throw new Error(`${path}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

let socket: WebSocket | null = null;
let messageListeners: ((message: ServerMessage) => void)[] = [];
let stateListeners: ((state: ConnectionState) => void)[] = [];
let reconnectAttempts = 0;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let closedByUs = false;

function announce(state: ConnectionState) {
  stateListeners.forEach((fn) => fn(state));
}

function openSocket() {
  if (typeof window === "undefined") return; // SSR
  if (socket && socket.readyState <= WebSocket.OPEN) return;

  announce("connecting");
  const ws = new WebSocket(`${BASE.replace(/^http/, "ws")}/ws`);
  socket = ws;

  ws.onopen = () => {
    reconnectAttempts = 0;
    announce("open");
  };

  ws.onmessage = (event) => {
    let message: ServerMessage;
    try {
      message = JSON.parse(event.data as string);
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
  send(key: string, value: ParamValue) {
    const wire = toWire(value);
    if (socketReady()) {
      socket!.send(JSON.stringify({ type: "set", name: key, value: wire }));
      return;
    }
    void request(`/api/parameter/${key}`, {
      method: "PUT",
      body: JSON.stringify({ value: wire }),
    }).catch((error) => console.error("[katana]", error));
  },

  /** Footswitch-style CC message. */
  sendCC(cc: number, value: number) {
    void request(`/api/cc/${cc}`, {
      method: "POST",
      body: JSON.stringify({ value }),
    }).catch((error) => console.error("[katana]", error));
  },

  /** Switch tone-setting channel. The amp reloads, so a whole new state follows. */
  selectChannel(id: string) {
    if (socketReady()) {
      socket!.send(JSON.stringify({ type: "channel", name: id }));
      return;
    }
    void request(`/api/channel/${id}`, { method: "POST" }).catch((error) =>
      console.error("[katana]", error),
    );
  },

  /** Copy the live sound into a stored channel. Overwrites it permanently. */
  async saveToPatch(number: number) {
    return request<{ patch: number; names: Record<string, string> }>(
      `/api/patch/${number}`,
      { method: "POST" },
    );
  },

  /** Server-side treadle sweep - one request, never stepped from the browser. */
  sweepWah(from: number, to: number, ms: number) {
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

  /** Everything the amp currently reports. */
  async state() {
    return request<Record<string, number>>("/api/state");
  },

  /** Full state re-read. The amp never reports physical knob turns. */
  async resync() {
    return request<Record<string, number>>("/api/refresh", { method: "POST" });
  },

  /** Channel list and the names of the stored patches. */
  async channels() {
    return request<{
      channels: Record<string, number>;
      patches: Record<string, string>;
    }>("/api/channels");
  },

  /** .tsl files on the server and the patches inside them. */
  async patchFiles() {
    return request<
      { file: string; patches?: { index: number; name: string }[]; error?: string }[]
    >("/api/tsl");
  },

  async loadPatchFile(file: string, index: number) {
    return request<{ name: string; applied: number; skipped: string[] }>(
      `/api/tsl/${encodeURIComponent(file)}/${index}`,
      { method: "POST" },
    );
  },

  onMessage(fn: (message: ServerMessage) => void) {
    messageListeners.push(fn);
    return () => {
      messageListeners = messageListeners.filter((l) => l !== fn);
    };
  },

  onConnectionChange(fn: (state: ConnectionState) => void) {
    stateListeners.push(fn);
    return () => {
      stateListeners = stateListeners.filter((l) => l !== fn);
    };
  },
};
