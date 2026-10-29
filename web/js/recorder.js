// The recorder's store: the take being recorded, and the finished ones.
//
// The server is the truth. It sends a "recorder" message whenever its
// state changes - four times a second while recording, as the time and
// the peak move - and a "recordings" list when a take is added or deleted.
// Takes play in the browser straight from the Pi.

import { transport } from "./transport.js";
import { clock } from "./practice.js";

const CLIPPED = 0.999;   // a peak this high means the amp's output clipped

/** "2026-10-29 16-05-32 seek and destroy.wav" -> { when: "2026-10-29 16:05", song: "seek and destroy" } */
export function describe(name) {
  const parts = name.match(/^(\d{4}-\d\d-\d\d) (\d\d)-(\d\d)-\d\d(?: (.+))?\.wav$/);
  if (!parts) return { when: name.replace(/\.wav$/, ""), song: null };
  return { when: `${parts[1]} ${parts[2]}:${parts[3]}`, song: parts[4] ?? null };
}

export function createRecorderStore() {
  return {
    available: false,
    recording: false,
    saving: false,
    elapsed: 0,
    peak: 0,              // loudest sample of the take, 0..1
    error: null,
    takes: [],            // [{ name, seconds, bytes }], newest first
    selected: null,       // the take open for listening
    pendingDelete: null,  // the take waiting for "are you sure?"

    // ---- reads ----
    // The server keeps the last take's time and peak after it stops; the
    // plate shows them only while there is a take on the go.
    get active() { return this.recording || this.saving; },
    get time() { return this.active ? this.elapsed : 0; },
    get clipped() { return this.active && this.peak >= CLIPPED; },
    /** The peak as dB below full scale: 0.5 -> "−6 dB". */
    get peakLabel() {
      if (!this.active || this.peak <= 0) return "–";
      const decibels = Math.round(20 * Math.log10(this.peak));
      return decibels >= 0 ? "0 dB" : `−${Math.abs(decibels)} dB`;
    },
    /** How full the meter is: -48 dB and below empty, 0 dB full. */
    get meter() {
      if (!this.active || this.peak <= 0) return 0;
      return Math.min(Math.max(1 + 20 * Math.log10(this.peak) / 48, 0), 1);
    },
    get status() {
      if (this.saving) return "saving…";
      if (this.recording) return "recording";
      return "";
    },
    url(name, download = false) { return transport.recordingUrl(name, download); },
    describe,
    clock,

    // ---- actions ----
    toggle() {
      transport.recorder(this.recording ? "stop" : "start");
    },

    select(name) {
      this.selected = this.selected === name ? null : name;
    },

    askDelete(name) {
      this.pendingDelete = name;
    },

    async confirmDelete() {
      const name = this.pendingDelete;
      this.pendingDelete = null;
      if (this.selected === name) this.selected = null;
      try {
        await transport.deleteRecording(name);
      } catch (error) {
        console.error("[recorder] delete failed", error);
      }
    },

    init() {
      transport.onMessage((message) => {
        if (message.type === "recorder") {
          Object.assign(this, {
            available: message.available,
            recording: message.recording ?? false,
            saving: message.saving ?? false,
            elapsed: message.elapsed ?? 0,
            peak: message.peak ?? 0,
            error: message.error ?? null,
          });
        } else if (message.type === "recordings") {
          this.takes = message.recordings;
          if (!this.takes.some((take) => take.name === this.selected)) this.selected = null;
        }
      });
    },
  };
}
