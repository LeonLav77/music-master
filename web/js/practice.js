// The practice tab's store: the metronome and the backing tracks.
//
// The server is the truth. Everything it plays comes back as a "playback"
// or "tracks" message, to every open page - including changes nobody sent,
// like a song ending. The one exception is a value being edited here: an
// echo of an older value must not undo it, so incoming values for a field
// edited in the last EDIT_GRACE_MS are skipped.
//
// The server does not stream the playing position. It sends it when
// something changes, and the page counts on from there.

import { transport } from "./transport.js";

const EDIT_GRACE_MS = 600;
const TAP_RESET_MS = 2000;   // a pause this long starts a new tap tempo
const SETTINGS_KEY = "katana.practice.tracks";

// Count-in tempo, beat 1 and count-in length per song. Kept in this
// browser for now, so a phone and a laptop each remember their own.
function loadSettings() {
  try {
    return JSON.parse(localStorage.getItem(SETTINGS_KEY)) ?? {};
  } catch {
    return {};
  }
}

function saveSettings(settings) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {}
}

function clamp(value, low, high) {
  return Math.min(Math.max(value, low), high);
}

/** "seek_and_destroy.m4a" -> "seek and destroy" */
export function displayName(name) {
  return name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ");
}

/** 75.4 -> "1:15" */
export function clock(seconds) {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function createPracticeStore() {
  return {
    available: false,
    loading: null,
    metronome: { running: false, bpm: 120, beats_per_bar: 4, volume: 1 },
    track: null,          // { name, playing, elapsed, duration, volume } from the server
    tracks: [],           // [{ name, ready }], newest first
    selected: null,
    receivedAt: 0,        // when track.elapsed was measured
    now: 0,               // ticks while the page is open, so the progress bar moves

    _settings: loadSettings(),
    _editedAt: {},
    _taps: [],

    // ---- reads ----
    settingsFor(name) {
      return { bpm: 120, firstBeat: 0, countIn: 4, ...this._settings[name] };
    },
    get song() {
      return this.selected ? this.settingsFor(this.selected) : null;
    },
    /** The selected song is the one loaded in the player. */
    get isCurrent() {
      return this.track !== null && this.track.name === this.selected;
    },
    /** Started, but still in the count-in: the song has not moved yet. */
    get countingIn() {
      return this.track?.playing === true && this.metronome.running;
    },
    get elapsed() {
      if (!this.isCurrent) return 0;
      if (!this.track.playing || this.countingIn) return this.track.elapsed;
      const since = (this.now - this.receivedAt) / 1000;
      return Math.min(this.track.elapsed + since, this.track.duration);
    },
    get duration() {
      return this.isCurrent ? this.track.duration : 0;
    },
    get status() {
      if (this.loading === this.selected) return "loading…";
      if (!this.isCurrent) return "stopped";
      if (this.countingIn) return "count-in";
      if (this.track.playing) return "playing";
      return this.track.elapsed > 0 ? "paused" : "stopped";
    },
    isReady(name) {
      return this.tracks.find((entry) => entry.name === name)?.ready === true;
    },
    displayName,
    clock,

    // ---- metronome ----
    _edited(key) {
      this._editedAt[key] = performance.now();
    },

    setMetronome(fields) {
      for (const [key, value] of Object.entries(fields)) {
        this.metronome[key] = value;
        this._edited(key);
      }
      transport.metronome(fields);
    },

    setBpm(bpm) {
      this.setMetronome({ bpm: clamp(Math.round(bpm), 20, 400) });
    },

    toggleMetronome() {
      this.setMetronome({ running: !this.metronome.running });
    },

    /** Tap tempo: the average gap between the last few taps. Returns the
     *  BPM once there are two taps, null before that. */
    tap() {
      const now = performance.now();
      if (this._taps.length && now - this._taps[this._taps.length - 1] > TAP_RESET_MS) {
        this._taps = [];
      }
      this._taps = [...this._taps, now].slice(-5);
      if (this._taps.length < 2) return null;
      const gaps = this._taps.slice(1).map((time, index) => time - this._taps[index]);
      const average = gaps.reduce((sum, gap) => sum + gap, 0) / gaps.length;
      return clamp(Math.round(60000 / average), 20, 400);
    },

    tapMetronome() {
      const bpm = this.tap();
      if (bpm !== null) this.setBpm(bpm);
    },

    // ---- tracks ----
    select(name) {
      this.selected = name;
    },

    updateSong(fields) {
      this._settings = {
        ...this._settings,
        [this.selected]: { ...this.settingsFor(this.selected), ...fields },
      };
      saveSettings(this._settings);
    },

    tapSong() {
      const bpm = this.tap();
      if (bpm !== null) this.updateSong({ bpm });
    },

    play() {
      const song = this.song;
      // The count-in plays at the song's tempo. Both go down the same
      // socket in order, so the tempo is set before the play runs.
      this.setMetronome({ bpm: song.bpm });
      transport.track("play", { name: this.selected, count_in: song.countIn, first_beat: song.firstBeat });
    },

    pause() {
      transport.track("pause");
    },

    resume() {
      transport.track("resume");
    },

    stop() {
      transport.track("stop");
    },

    seek(seconds) {
      transport.track("seek", { seconds: clamp(seconds, 0, this.duration) });
    },

    setTrackVolume(value) {
      if (this.track) this.track.volume = value;
      this._edited("track_volume");
      transport.track("volume", { value });
    },

    // ---- from the server ----
    _recent(key) {
      return performance.now() - (this._editedAt[key] ?? -Infinity) < EDIT_GRACE_MS;
    },

    _apply(message) {
      this.available = message.available;
      if (!message.available) return;
      this.loading = message.loading;
      for (const [key, value] of Object.entries(message.metronome)) {
        if (!this._recent(key)) this.metronome[key] = value;
      }
      const track = message.track;
      if (track && this._recent("track_volume") && this.track) track.volume = this.track.volume;
      this.track = track;
      this.receivedAt = performance.now();
      this.now = this.receivedAt;
    },

    init() {
      transport.onMessage((message) => {
        if (message.type === "playback") {
          this._apply(message);
        } else if (message.type === "tracks") {
          this.tracks = message.tracks;
          const names = message.tracks.map((entry) => entry.name);
          if (!names.includes(this.selected)) this.selected = this.track?.name ?? names[0] ?? null;
        }
      });
      setInterval(() => {
        this.now = performance.now();
      }, 250);
    },
  };
}
