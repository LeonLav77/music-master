// The tuner: the note the guitar is playing, as the server hears it.
//
// The server listens all the time. While a note rings it sends a "tuner"
// message with every new reading - about 14 a second - and one with
// note: null when the note stops. Nothing goes the other way.

import { transport } from "./transport.js";

const IN_TUNE_CENTS = 3;   // this close to the note counts as in tune

export function createTunerStore() {
  return {
    available: false,
    note: null,      // "E", or null when nothing is ringing
    octave: null,
    cents: 0,        // kept when the note stops, so the dot fades where it was

    get ringing() { return this.note !== null; },
    get inTune() { return this.ringing && Math.abs(this.cents) <= IN_TUNE_CENTS; },
    /** Where the dot sits along the scale: 0% is 50 cents flat, 100% 50 sharp. */
    get position() { return 50 + Math.max(-50, Math.min(50, this.cents)); },
    /** -3.4 -> "−3 ¢" */
    get centsLabel() {
      if (!this.ringing) return "";
      const whole = Math.round(this.cents);
      if (whole === 0) return "0 ¢";
      return `${whole > 0 ? "+" : "−"}${Math.abs(whole)} ¢`;
    },

    init() {
      transport.onMessage((message) => {
        if (message.type !== "tuner") return;
        this.available = message.available;
        this.note = message.available ? message.note : null;
        if (this.note !== null) {
          this.octave = message.octave;
          this.cents = message.cents;
        }
      });
    },
  };
}

/** The bubble beside EQ: small, or opened up big. A phone ignores this
 *  and always shows it open, as a section at the bottom of the page. */
export function tunerDock() {
  return {
    expanded: localStorage.getItem("katana.tuner.expanded") === "1",
    toggleExpanded() {
      this.expanded = !this.expanded;
      try { localStorage.setItem("katana.tuner.expanded", this.expanded ? "1" : "0"); } catch {}
    },
  };
}
