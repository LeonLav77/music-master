import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { PARAM_BY_KEY } from "./generated";
import { CHANNELS, EQ_BANDS, type ChannelId, type LedColor } from "./schema";
import {
  transport,
  type ConnectionState,
  type ParamValue,
  type ServerMessage,
} from "./transport";

export const UNKNOWN = "unknown" as const;
export type StoredValue = ParamValue | typeof UNKNOWN;

type State = Record<string, StoredValue>;

const offlineDefaults: State = {
  amp_type: 7,
  gain: 78,
  bass: 62,
  middle: 34,
  treble: 71,
  presence: 58,
  volume: 55,
  bright: false,
  knob_volume: 64,

  boost_switch: true,
  boost_type: 11,
  boost_drive: 42,
  boost_bottom: 55,
  boost_tone: 60,
  boost_level: 70,
  boost_direct_mix: 0,
  boost_solo_level: 50,
  boost_solo_switch: false,

  delay_switch: true,
  delay_type: 0,
  delay_time: 420,
  delay_feedback: 32,
  delay_high_cut: 9,
  delay_level: 44,
  delay_direct_mix: 100,

  delay2_switch: false,
  delay2_type: 3,
  delay2_time: 640,
  delay2_feedback: 24,
  delay2_high_cut: 7,
  delay2_level: 30,
  delay2_direct_mix: 100,

  reverb_switch: true,
  reverb_type: 1,
  reverb_time: 41,
  reverb_level: 38,
  reverb_direct_mix: 100,

  pedal_switch: false,
  pedal_type: 0,
  wah_type: 0,
  wah_position: 20,
  wah_pedal_min: 0,
  wah_pedal_max: 100,
  wah_level: 60,
  wah_direct_mix: 0,

  eq_switch: true,
  eq_type: false,
  eq_level: 24,

  noise_suppressor_switch: true,
  noise_suppressor_threshold: 46,
  noise_suppressor_release: 52,

  fx1_switch: false,
  fx1_type: 14,
  fx2_switch: false,
  fx2_type: 3,

  led_boost: 2,
  led_mod: 0,
  led_fx: 0,
  led_delay: 1,
  led_reverb: 3,
};

// Pantera-style reference curve from the control reference.
const eqSeed = [14, 14, 12, -6, -12, -15, -7, 8, 10, 11];
EQ_BANDS.forEach((b, i) => {
  offlineDefaults[b.key] = eqSeed[i] ?? 0;
});

/** The amp reports 0/1 for switches; the UI wants real booleans. */
function fromWire(key: string, value: number): ParamValue {
  return PARAM_BY_KEY[key]?.kind === "toggle" ? value !== 0 : value;
}

/** Resolve when the amp confirms it is on `id`, or after a sensible wait.
 *  A channel change takes a few seconds of MIDI; the confirmation is the
 *  "channel" frame the server pushes once it has re-read everything. */
function waitForChannel(id: string, timeout = 8000): Promise<void> {
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

function decode(values: Record<string, number>): State {
  const out: State = {};
  for (const [key, value] of Object.entries(values)) {
    out[key] = fromWire(key, value);
  }
  return out;
}

type Ctx = {
  state: State;
  get: (key: string) => StoredValue;
  num: (key: string) => number;
  bool: (key: string) => boolean;
  set: (key: string, value: ParamValue) => void;
  toggle: (key: string) => void;
  channel: ChannelId;
  channelNames: Record<ChannelId, string>;
  selectChannel: (id: ChannelId) => void;
  saveToChannel: (id: ChannelId) => void;
  led: (key: string) => LedColor;
  resync: () => void;
  /** Tell the store a control is being dragged, so pushes do not fight it. */
  hold: (key: string, holding: boolean) => void;
  /** Switch the wah on properly, or off. */
  setWah: (on: boolean) => void;
  /** Something slow is happening on the amp - switching channel, loading a
   *  patch. Roughly 2-5 s of MIDI, during which the UI should not pretend
   *  it is idle or accept another one. */
  busy: string | null;
  runBusy: <T>(label: string, work: () => Promise<T>) => Promise<T | undefined>;
  connection: ConnectionState;
  /** True once the amp's real state has been read at least once. */
  live: boolean;
  syncing: boolean;
  lastSync: Date | null;
  dirty: boolean;
};

const KatanaContext = createContext<Ctx | null>(null);

export function KatanaProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>(offlineDefaults);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [live, setLive] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  // Lets callbacks read the latest state without re-creating themselves.
  const stateRef = useRef<State>(offlineDefaults);
  stateRef.current = state;

  // Keys the user is currently dragging. An update arriving from the amp
  // must not yank a control out from under a finger.
  const held = useRef(new Set<string>());
  const [channel, setChannel] = useState<ChannelId>("a1");
  const [channelNames, setChannelNames] = useState<Record<ChannelId, string>>(
    () =>
      Object.fromEntries(CHANNELS.map((c) => [c.id, c.name])) as Record<ChannelId, string>,
  );
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [dirty, setDirty] = useState(false);

  const set = useCallback((key: string, value: ParamValue) => {
    setState((s) => (s[key] === value ? s : { ...s, [key]: value }));
    setDirty(true);
    transport.send(key, value);
  }, []);

  const runBusy = useCallback(
    async <T,>(label: string, work: () => Promise<T>) => {
      setBusy(label);
      try {
        return await work();
      } catch (error) {
        console.error("[katana]", label, error);
        return undefined;
      } finally {
        setBusy(null);
      }
    },
    [],
  );

  // The pedal section also does pedal-bend, so switching it on is not
  // enough - it has to be pointed at wah first, or the treadle moves
  // something else entirely. Same trap the amp itself sets.
  const setWah = useCallback(
    (on: boolean) => {
      if (on) {
        setState((s) => ({ ...s, pedal_type: 0, pedal_switch: true }));
        transport.send("pedal_type", 0);
        transport.send("pedal_switch", true);
      } else {
        setState((s) => ({ ...s, pedal_switch: false }));
        transport.send("pedal_switch", false);
      }
      setDirty(true);
    },
    [],
  );

  const hold = useCallback((key: string, holding: boolean) => {
    if (holding) held.current.add(key);
    else held.current.delete(key);
  }, []);

  // The send must not live inside a setState updater: React re-runs
  // updaters (twice under StrictMode, and again on retries), which would
  // fire a MIDI write each time.
  const toggle = useCallback((key: string) => {
    const next = !(stateRef.current[key] === true);
    setState((s) => ({ ...s, [key]: next }));
    transport.send(key, next);
    setDirty(true);
  }, []);

  const selectChannel = useCallback(
    (id: ChannelId) => {
      setChannel(id);
      setDirty(false);
      // Program Change, not CC. The amp reloads and pushes a whole new
      // state, which takes a few seconds - hold `busy` until it lands so
      // the UI can say so instead of looking frozen.
      void runBusy(`loading ${id.toUpperCase()}`, async () => {
        transport.selectChannel(id);
        await waitForChannel(id);
      });
    },
    [runBusy],
  );

  const saveToChannel = useCallback(async (id: ChannelId) => {
    const pc = CHANNELS.find((c) => c.id === id)?.pc;
    if (pc === undefined) return;
    try {
      const result = await runBusy(`saving to ${id.toUpperCase()}`, () =>
        transport.saveToPatch(pc),
      );
      if (!result) return;
      setChannelNames((names) => ({
        ...names,
        ...(Object.fromEntries(
          CHANNELS.map((c) => [c.id, result.names[String(c.pc)] ?? names[c.id]]),
        ) as Record<ChannelId, string>),
      }));
      setChannel(id);
      setDirty(false);
    } catch (error) {
      console.error("[katana] save failed", error);
    }
  }, [runBusy]);

  const resync = useCallback(async () => {
    setSyncing(true);
    try {
      const values = await transport.resync();
      setState((s) => ({ ...s, ...decode(values) }));
      setLive(true);
      setLastSync(new Date());
      setDirty(false);
    } catch (error) {
      console.error("[katana] resync failed", error);
    } finally {
      setSyncing(false);
    }
  }, []);

  // Open the socket and take the amp's real state as the truth.
  useEffect(() => {
    let cancelled = false;

    const offState = transport.onConnectionChange(setConnection);
    const offMessage = transport.onMessage((message: ServerMessage) => {
      if (cancelled) return;
      switch (message.type) {
        case "state":
        case "channel":
        case "patch": {
          setState((s) => {
            const next = { ...s, ...decode(message.values) };
            // Keep whatever the user is holding onto right now.
            held.current.forEach((key) => {
              if (key in s) next[key] = s[key] as StoredValue;
            });
            return next;
          });
          setLive(true);
          setLastSync(new Date());
          if (message.type === "channel") {
            setChannel(message.channel as ChannelId);
            setDirty(false);
          }
          break;
        }
        case "parameter": {
          if (held.current.has(message.name)) break;
          setState((s) => ({
            ...s,
            [message.name]: fromWire(message.name, message.value),
          }));
          break;
        }
        case "patches": {
          setChannelNames((names) => ({
            ...names,
            ...(Object.fromEntries(
              CHANNELS.map((c) => [c.id, message.names[String(c.pc)] ?? names[c.id]]),
            ) as Record<ChannelId, string>),
          }));
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
      .then(({ patches }) => {
        if (cancelled) return;
        setChannelNames(
          (names) =>
            Object.fromEntries(
              CHANNELS.map((c) => [c.id, patches[String(c.pc)] ?? names[c.id]]),
            ) as Record<ChannelId, string>,
        );
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
      offState();
      offMessage();
      transport.disconnect();
    };
  }, []);

  const value = useMemo<Ctx>(
    () => ({
      state,
      get: (k) => (k in state ? (state[k] as StoredValue) : UNKNOWN),
      num: (k) => (typeof state[k] === "number" ? (state[k] as number) : 0),
      bool: (k) => state[k] === true,
      set,
      toggle,
      channel,
      channelNames,
      selectChannel,
      saveToChannel,
      led: (k) => {
        const v = state[k];
        const colors: LedColor[] = ["off", "green", "red", "yellow"];
        return colors[typeof v === "number" ? v : 0] ?? "off";
      },
      resync,
      connection,
      live,
      hold,
      setWah,
      busy,
      runBusy,
      syncing,
      lastSync,
      dirty,
    }),
    [
      state,
      connection,
      live,
      hold,
      setWah,
      busy,
      runBusy,
      set,
      toggle,
      channel,
      channelNames,
      selectChannel,
      saveToChannel,
      resync,
      syncing,
      lastSync,
      dirty,
    ],
  );

  return <KatanaContext.Provider value={value}>{children}</KatanaContext.Provider>;
}

export function useKatana() {
  const ctx = useContext(KatanaContext);
  if (!ctx) throw new Error("useKatana must be used inside <KatanaProvider>");
  return ctx;
}
