// The aux deck: backing-track playback, as its own Alpine store.
//
// Separate from the katana store for the same reason server/audio.py is
// separate from server/api.py - the deck and the amp share a page and
// nothing else. Nothing here reads or writes a single amp parameter, and
// the deck keeps working with the amp switched off.
//
// One thing genuinely differs from the amp side. The amp pushes a message
// per change and the store is otherwise passive; the player's position
// moves continuously and nothing pushes each tick, so position is
// *predicted* locally from a clock and corrected whenever the server does
// say something. That keeps the playhead smooth at 60fps without a message
// per frame, at the cost of drifting a fraction of a second between
// corrections - inaudible, and the count-in is built server-side where it
// has to be exact.

import { transport } from "./transport.js";

/** Seconds to "3:52". */
export function clock(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const whole = Math.floor(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function createDeckStore() {
  return {
    tracks: [],
    sinks: [],
    sink: null,

    // What the server last told us, and when we heard it. Position is
    // derived from these rather than stored, so a stale frame cannot leave
    // the playhead parked in the wrong place.
    serverState: "stopped",
    serverPosition: 0,
    serverAt: 0,
    track: null,
    duration: null,
    countInRemaining: 0,

    // A local tick, so the playhead moves between server frames.
    now: 0,

    // ---- settings, all local ----
    volume: 0.7,
    // Make-up gain in dB. Separate from `volume` because they are different
    // operations: volume only turns the track down and is free, this pushes
    // it above its own recorded level and costs an ffmpeg pass before
    // playback starts. 0 leaves the audio untouched.
    boostDb: 0,
    maxBoostDb: 12,
    countIn: true,
    bpm: 120,
    bars: 1,
    beatsPerBar: 4,
    loop: false,

    filter: "",
    fetching: false,
    error: null,
    busy: false,

    _timer: null,
    // Guards the end-of-track handler. The tick fires every 100ms and does
    // not await, while a loop restart is a round-trip: without this, a
    // track that has reached its end fires a fresh play on every tick
    // until the first response lands, and each one stops the track the
    // previous one just started.
    _ending: false,
    // Fader throttling - see setVolume.
    _volumeInFlight: false,
    _pendingVolume: null,

    async init() {
      // The socket is already open for the amp; the deck just listens for
      // its own frames on it.
      transport.onMessage((message) => this.receive(message));

      await this.reload();
      try {
        this.maxBoostDb = (await transport.audioLimits()).max_boost_db;
      } catch {
        // Keep the built-in default; the server will reject anything over
        // its own ceiling anyway.
      }
      try {
        const { sinks, default: preferred } = await transport.sinks();
        this.sinks = sinks;
        this.sink = preferred;
      } catch (error) {
        this.error = String(error.message ?? error);
      }

      // Catch up on a track that was already playing - the page may have
      // been reloaded mid-song, and the server is the one that knows.
      try {
        this.apply(await transport.audioStatus());
      } catch {
        // A deck that cannot reach the server is not an error worth
        // showing: the amp side's connection indicator already says so.
      }

      // 10 Hz is enough for a playhead and a countdown; the actual
      // smoothness comes from the CSS transition on the head, not from
      // ticking faster.
      this._timer = setInterval(() => {
        this.now = Date.now();
        // A track that has played out stops on its own server-side; ask
        // once we predict it should have finished rather than polling.
        if (!this._ending && this.serverState === "playing" && this.duration
            && this.position >= this.duration) {
          void this.finished();
        }
      }, 100);
    },

    /** Adopt a status frame from the server. */
    apply(status) {
      if (!status) return;
      this.serverState = status.state;
      this.serverPosition = status.position ?? 0;
      this.serverAt = Date.now();
      this.track = status.track;
      this.duration = status.duration;
      this.countInRemaining = status.count_in_remaining ?? 0;
      if (status.sink) this.sink = status.sink;
      this.now = Date.now();
    },

    receive(message) {
      if (message.type === "audio") this.apply(message);
      if (message.type === "fetch") {
        this.fetching = message.state === "started";
        if (message.state === "done") void this.reload();
        if (message.state === "failed") this.error = message.detail;
      }
    },

    // ---- derived ----

    /** Seconds into the track, predicted forward from the last frame.
     *
     * Elapsed time is spent on the count-in first. The server reports
     * position 0 for the whole click - the track genuinely has not started
     * - so without this the playhead would crawl forward while the click
     * was still running, and the track would then appear to start late by
     * exactly the length of the count-in.
     */
    get position() {
      if (this.serverState !== "playing") return this.serverPosition;
      const elapsed = (this.now - this.serverAt) / 1000;
      const afterClick = Math.max(0, elapsed - this.countInRemaining);
      const at = this.serverPosition + afterClick;
      return this.duration ? Math.min(at, this.duration) : at;
    },

    get playing() { return this.serverState === "playing"; },
    get paused() { return this.serverState === "paused"; },
    get stopped() { return this.serverState === "stopped"; },
    get active() { return this.serverState !== "stopped"; },

    /** Still in the click, before the track proper. */
    get counting() {
      return this.playing && this.countdown > 0;
    },

    /** Seconds of count-in left, predicted like position. */
    get countdown() {
      if (this.serverState !== "playing" || !this.countInRemaining) return 0;
      const elapsed = (this.now - this.serverAt) / 1000;
      return Math.max(0, this.countInRemaining - elapsed);
    },

    get progress() {
      if (!this.duration) return 0;
      return Math.min(100, (this.position / this.duration) * 100);
    },

    get elapsedLabel() { return clock(this.position); },
    get durationLabel() { return this.duration ? clock(this.duration) : "--:--"; },

    /** How long the click will run, in seconds. */
    get countInSeconds() {
      if (!this.countIn || !this.bpm) return 0;
      return (this.bars * this.beatsPerBar) * (60 / this.bpm);
    },

    get beats() { return this.bars * this.beatsPerBar; },

    /** Which beat the click is on, or -1. Drives the pips. */
    get currentBeat() {
      if (!this.counting) return -1;
      const done = this.countInSeconds - this.countdown;
      return Math.floor(done / (60 / this.bpm));
    },

    get visibleTracks() {
      const q = this.filter.trim().toLowerCase();
      if (!q) return this.tracks;
      return this.tracks.filter((t) => t.name.toLowerCase().includes(q));
    },

    /** The one status line the deck shows. */
    get label() {
      if (this.error) return this.error;
      if (this.fetching) return "fetching…";
      if (this.counting) return `counting in — ${this.countdown.toFixed(1)}s`;
      if (this.playing) return "playing to aux";
      if (this.paused) return "paused";
      return this.tracks.length ? "ready" : "no tracks yet";
    },

    /** Above this the analog jack clips - see scripts/aux-play.sh. */
    get hot() { return this.volume > 0.85; },

    /** What the boost is actually doing, in words.
     *
     * The returns diminish sharply - measured on this library, +3 dB buys
     * 2.0 dB of real loudness and +12 dB only 3.8 dB, because past about
     * +6 the limiter is flattening the track rather than raising it. Worth
     * saying out loud, since the number alone implies it keeps scaling.
     */
    get boostLabel() {
      if (!this.boostDb) return "off — track plays at its own level";
      if (this.boostDb <= 6) return `+${this.boostDb} dB — louder, peaks limited`;
      return `+${this.boostDb} dB — loud, dynamics squashed`;
    },

    /** Set the output level, live if something is playing.
     *
     * Throttled: this fires on every step of a fader drag, and each call
     * is an HTTP round-trip and a pw-dump on the server. One in-flight
     * request at a time with the latest value sent after it lands keeps a
     * drag smooth without queueing fifty stale levels behind it.
     */
    setVolume(v) {
      this.volume = Math.min(1, Math.max(0, v));
      if (!this.active) return;
      this._pendingVolume = this.volume;
      if (this._volumeInFlight) return;
      this._volumeInFlight = true;
      const send = () => {
        const next = this._pendingVolume;
        this._pendingVolume = null;
        transport.setVolume(next)
          .catch(() => {})
          .then(() => {
            if (this._pendingVolume !== null) send();
            else this._volumeInFlight = false;
          });
      };
      send();
    },

    /** A boost rebuilds the audio, so a running track has to restart.
     *
     * It restarts where it was rather than at the top: this is a mixing
     * decision made mid-song, usually because the track is sitting wrong
     * against the room, and throwing the player back to bar one every time
     * would make it unusable for that. No count-in either - you are already
     * playing, so there is nothing to count into.
     *
     * A paused track keeps its position and stays paused; restarting it
     * would be a play nobody asked for.
     */
    async applyBoost(db) {
      if (db === this.boostDb) return;
      this.boostDb = db;
      if (!this.playing || !this.track) return;
      await this.start(this.track, { from: this.position, click: false });
    },

    // ---- actions ----

    async reload() {
      try {
        this.tracks = await transport.tracks();
        this.error = null;
      } catch (error) {
        this.error = String(error.message ?? error);
      }
    },

    /** Run one transport call, surfacing whatever the server says. */
    async run(fn) {
      this.busy = true;
      this.error = null;
      try {
        this.apply(await fn());
      } catch (error) {
        // The server's detail is the useful part; the URL prefix is not.
        const text = String(error.message ?? error);
        this.error = text.replace(/^\/api\/audio\/\w+:\s*/, "").replace(/^\{"detail":"|"\}$/g, "");
      } finally {
        this.busy = false;
      }
    },

    async start(file, { from = 0, click = true } = {}) {
      await this.run(() => transport.play({
        track: file,
        volume: this.volume,
        sink: this.sink,
        start: from,
        // A count-in only makes sense at the top of a deliberate start:
        // halfway through a song it is nonsense, and on a loop or a
        // settings change it would interrupt the thing it counted into.
        bpm: click && this.countIn && from === 0 ? this.bpm : null,
        bars: this.bars,
        beatsPerBar: this.beatsPerBar,
        boostDb: this.boostDb,
      }));
    },

    /** The one button that does the obvious thing whatever the state. */
    async toggle(file) {
      if (this.paused) return this.run(() => transport.resumeAudio());
      if (this.playing) return this.run(() => transport.pauseAudio());
      const target = file ?? this.track ?? this.tracks[0]?.file;
      if (target) await this.start(target);
    },

    async stop() { await this.run(() => transport.stopAudio()); },

    async seek(seconds) {
      if (!this.active) return;
      await this.run(() => transport.seekAudio(Math.max(0, seconds)));
    },

    /** Called when a track plays out. Loops, or settles to stopped. */
    async finished() {
      if (this._ending) return;
      this._ending = true;
      try {
        // Read the track before any await: a loop restart clears it
        // server-side, and `this.track` follows the server.
        const again = this.loop ? this.track : null;
        if (again) {
          // No click on a repeat: the count-in exists to get you in at the
          // top of a take, and hearing it every lap of a loop you are
          // already playing over is an interruption, not a cue.
          await this.start(again, { click: false });
          return;
        }
        // Confirm with the server rather than assuming - our prediction of
        // the end is a tenth of a second either way.
        this.apply(await transport.audioStatus());
      } catch {
        this.serverState = "stopped";
      } finally {
        this._ending = false;
      }
    },

    /** Select a track: adopt its tempo if we know one, and play it. */
    async choose(track) {
      await this.start(track.file);
    },

    async fetch(url) {
      if (!url.trim()) return;
      this.fetching = true;
      this.error = null;
      try {
        await transport.fetchTrack(url.trim());
        await this.reload();
      } catch (error) {
        const text = String(error.message ?? error);
        this.error = text.replace(/^\/api\/audio\/fetch:\s*/, "").replace(/^\{"detail":"|"\}$/g, "");
      } finally {
        this.fetching = false;
      }
    },

    async remove(track) {
      try {
        await transport.deleteTrack(track.file);
        await this.reload();
      } catch (error) {
        this.error = String(error.message ?? error);
      }
    },
  };
}
