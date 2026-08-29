// The Katana store, as an Alpine global store.
//
// Alpine's reactivity is proxy-based and per-property, so unlike the React
// context this replaced, touching one parameter only re-renders the bindings
// that actually read it. There is no provider and no memoisation to keep in
// sync - `state` is a plain object and writing to a key is the update.

import { transport } from "./transport.js";
import { PARAM_BY_KEY, CHANNELS, EQ_BANDS, LED_COLORS } from "./schema.js";

export const UNKNOWN = "unknown";

const offlineDefaults = {
  amp_type: 7, gain: 78, bass: 62, middle: 34, treble: 71, presence: 58,
  volume: 55, bright: false, knob_volume: 64,

  boost_switch: true, boost_type: 11, boost_drive: 42, boost_bottom: 55,
  boost_tone: 60, boost_level: 70, boost_direct_mix: 0, boost_solo_level: 50,
  boost_solo_switch: false,

  delay_switch: true, delay_type: 0, delay_time: 420, delay_feedback: 32,
  delay_high_cut: 9, delay_level: 44, delay_direct_mix: 100,

  delay2_switch: false, delay2_type: 3, delay2_time: 640, delay2_feedback: 24,
  delay2_high_cut: 7, delay2_level: 30, delay2_direct_mix: 100,

  reverb_switch: true, reverb_type: 1, reverb_time: 41, reverb_level: 38,
  reverb_direct_mix: 100,

  pedal_switch: false, pedal_type: 0, wah_type: 0, wah_position: 20,
  wah_pedal_min: 0, wah_pedal_max: 100, wah_level: 60, wah_direct_mix: 0,

  eq_switch: true, eq_type: false, eq_level: 24,

  noise_suppressor_switch: true, noise_suppressor_threshold: 46,
  noise_suppressor_release: 52,

  fx1_switch: false, fx1_type: 14, fx2_switch: false, fx2_type: 3,

  led_boost: 2, led_mod: 0, led_fx: 0, led_delay: 1, led_reverb: 3,
};

// Pantera-style reference curve from the control reference.
const eqSeed = [14, 14, 12, -6, -12, -15, -7, 8, 10, 11];
EQ_BANDS.forEach((b, i) => {
  offlineDefaults[b.key] = eqSeed[i] ?? 0;
});

/** The amp reports 0/1 for switches; the UI wants real booleans. */
function fromWire(key, value) {
  return PARAM_BY_KEY[key]?.kind === "toggle" ? value !== 0 : value;
}

function decode(values) {
  const out = {};
  for (const [key, value] of Object.entries(values)) {
    out[key] = fromWire(key, value);
  }
  return out;
}

/** Resolve when the amp confirms it is on `id`, or after a sensible wait.
 *  A channel change takes a few seconds of MIDI; the confirmation is the
 *  "channel" frame the server pushes once it has re-read everything. */
function waitForChannel(id, timeout = 8000) {
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      off();
      resolve();
    };
    const timer = setTimeout(done, timeout);
    const off = transport.onMessage((message) => {
      if (message.type === "channel" && message.channel === id) done();
    });
  });
}

export function createKatanaStore() {
  return {
    state: { ...offlineDefaults },
    connection: "connecting",
    live: false,
    busy: null,
    channel: "a1",
    channelNames: Object.fromEntries(CHANNELS.map((c) => [c.id, c.name])),
    syncing: false,
    lastSync: null,
    dirty: false,

    // Keys the user is currently dragging. An update arriving from the amp
    // must not yank a control out from under a finger. A plain Set, kept off
    // the reactive state - nothing renders from it.
    _held: new Set(),

    // ---- reads ----
    get(key) {
      return key in this.state ? this.state[key] : UNKNOWN;
    },
    num(key) {
      return typeof this.state[key] === "number" ? this.state[key] : 0;
    },
    bool(key) {
      return this.state[key] === true;
    },
    led(key) {
      const v = this.state[key];
      return LED_COLORS[typeof v === "number" ? v : 0] ?? "off";
    },
    /** Formatted "synced HH:MM", or never. */
    get syncLabel() {
      return this.lastSync
        ? `synced ${this.lastSync.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
        : "never synced";
    },

    // ---- writes ----
    set(key, value) {
      if (this.state[key] === value) return;
      this.state[key] = value;
      this.dirty = true;
      transport.send(key, value);
    },

    toggle(key) {
      const next = !(this.state[key] === true);
      this.state[key] = next;
      transport.send(key, next);
      this.dirty = true;
    },

    /** Tell the store a control is being dragged, so pushes do not fight it. */
    hold(key, holding) {
      if (holding) this._held.add(key);
      else this._held.delete(key);
    },

    // The pedal section also does pedal-bend, so switching it on is not
    // enough - it has to be pointed at wah first, or the treadle moves
    // something else entirely. Same trap the amp itself sets.
    setWah(on) {
      if (on) {
        this.state.pedal_type = 0;
        this.state.pedal_switch = true;
        transport.send("pedal_type", 0);
        transport.send("pedal_switch", true);
      } else {
        this.state.pedal_switch = false;
        transport.send("pedal_switch", false);
      }
      this.dirty = true;
    },

    /** Something slow is happening on the amp - switching channel, loading a
     *  patch. Roughly 2-5 s of MIDI, during which the UI should not pretend
     *  it is idle or accept another one. */
    async runBusy(label, work) {
      this.busy = label;
      try {
        return await work();
      } catch (error) {
        console.error("[katana]", label, error);
        return undefined;
      } finally {
        this.busy = null;
      }
    },

    selectChannel(id) {
      this.channel = id;
      this.dirty = false;
      // Program Change, not CC. The amp reloads and pushes a whole new
      // state, which takes a few seconds - hold `busy` until it lands so
      // the UI can say so instead of looking frozen.
      void this.runBusy(`loading ${id.toUpperCase()}`, async () => {
        transport.selectChannel(id);
        await waitForChannel(id);
      });
    },

    async saveToChannel(id) {
      const pc = CHANNELS.find((c) => c.id === id)?.pc;
      if (pc === undefined) return;
      const result = await this.runBusy(`saving to ${id.toUpperCase()}`, () =>
        transport.saveToPatch(pc),
      );
      if (!result) return;
      this._mergeNames(result.names);
      this.channel = id;
      this.dirty = false;
    },

    async resync() {
      this.syncing = true;
      try {
        const values = await transport.resync();
        Object.assign(this.state, decode(values));
        this.live = true;
        this.lastSync = new Date();
        this.dirty = false;
      } catch (error) {
        console.error("[katana] resync failed", error);
      } finally {
        this.syncing = false;
      }
    },

    _mergeNames(names) {
      CHANNELS.forEach((c) => {
        const n = names[String(c.pc)];
        if (n) this.channelNames[c.id] = n;
      });
    },

    /** Apply an incoming full-state frame, preserving held controls. */
    _applyValues(values) {
      const next = decode(values);
      // Keep whatever the user is holding onto right now.
      this._held.forEach((key) => {
        if (key in this.state) delete next[key];
      });
      Object.assign(this.state, next);
      this.live = true;
      this.lastSync = new Date();
    },

    /** Open the socket and take the amp's real state as the truth. */
    init() {
      transport.onConnectionChange((s) => {
        this.connection = s;
      });

      transport.onMessage((message) => {
        switch (message.type) {
          case "state":
          case "channel":
          case "patch": {
            this._applyValues(message.values);
            if (message.type === "channel") {
              this.channel = message.channel;
              this.dirty = false;
            }
            break;
          }
          case "parameter": {
            if (this._held.has(message.name)) break;
            this.state[message.name] = fromWire(message.name, message.value);
            break;
          }
          case "patches": {
            this._mergeNames(message.names);
            break;
          }
          case "error":
            console.error("[katana]", message.detail);
            break;
        }
      });

      transport.connect();

      // Channel names are the amp's, not placeholders.
      transport
        .channels()
        .then(({ patches }) => this._mergeNames(patches))
        .catch(() => undefined);
    },
  };
}
