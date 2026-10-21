// Alpine component factories.
//
// Each returns an x-data object. Templates live in index.html; these hold
// only the behaviour and the derived geometry, so the markup stays readable.

import {
  dragValue, knobArc, knobAngle, KNOB_START, KNOB_SWEEP, KNOB_SIZES, KNOB_TICKS,
  eqPath, eqHit, eqGapFill, EQ_N, EQ_RANGE,
} from "./controls.js";
import { EQ_BANDS, AMP_MODEL_OPTIONS } from "./schema.js";
import { transport } from "./transport.js";

const store = () => Alpine.store("katana");

/** One amp knob. `key` is the parameter; omit `onSet` for a read-only knob. */
export function knob(key, label, { accent = "steel", size = "md", min = 0, max = 100, unit = "", disabled = false } = {}) {
  return {
    key, label, accent, size, min, max, unit, disabled,
    sizePx: KNOB_SIZES[size],
    ticks: KNOB_TICKS,
    trackPath: knobArc(KNOB_START, KNOB_START + KNOB_SWEEP),
    capId: `cap-${key}`,

    get value() { return store().num(this.key); },
    get angle() { return knobAngle(this.value, this.min, this.max); },
    get valuePath() { return knobArc(KNOB_START, this.angle + 0.01); },
    get readout() { return this.disabled ? `${Math.round(this.value)}${this.unit}` : `${Math.round(this.value)}${this.unit}`; },
    get interactive() { return !this.disabled; },

    drag: null,
    init() {
      const self = this;
      this.drag = dragValue({
        min, max,
        travel: size === "lg" ? 260 : 200,
        holdKey: key,
        hold: (k, h) => store().hold(k, h),
        get: () => store().num(self.key),
        set: (v) => store().set(self.key, v),
      });
    },
  };
}

/** Rotary amp-model selector. Dragging walks the option list; the amp's
 *  numbering is sparse, so step by position and translate back. */
export function ampDial(size = 180) {
  return {
    size,
    options: AMP_MODEL_OPTIONS,
    orbit: [
      { label: "clean", angle: -90 },
      { label: "crunch", angle: 0 },
      { label: "lead", angle: 90 },
      { label: "metal", angle: 180 },
    ],

    get value() { return store().num("amp_type"); },
    get index() {
      const i = this.options.findIndex((o) => o.value === this.value);
      return Math.max(0, i);
    },
    get name() {
      return this.options.find((o) => o.value === this.value)?.label ?? "—";
    },
    get pointerAngle() { return (this.index / this.options.length) * 360; },
    orbitStyle(o) {
      const rad = ((o.angle - 90) * Math.PI) / 180;
      const x = 50 + 38 * Math.cos(rad);
      const y = 50 + 38 * Math.sin(rad);
      return `left:${x}%;top:${y}%;transform:translate(-50%,-50%)`;
    },

    drag: null,
    init() {
      const self = this;
      this.drag = dragValue({
        min: 0,
        max: AMP_MODEL_OPTIONS.length - 1,
        travel: 260,
        holdKey: "amp_type",
        hold: (k, h) => store().hold(k, h),
        get: () => self.index,
        set: (i) => {
          const v = AMP_MODEL_OPTIONS[i]?.value;
          if (v !== undefined) store().set("amp_type", v);
        },
      });
    },
  };
}

/** The wah treadle: the whole slab is the pedal. */
export function treadle() {
  return {
    dragging: false,

    get value() { return store().num("wah_position"); },
    get min() { return store().num("wah_pedal_min"); },
    get max() { return store().num("wah_pedal_max"); },
    get on() { return store().bool("pedal_switch"); },
    // Tilt only backwards (0deg at heel-down, never past vertical). Rotating
    // toward the viewer scales the near edge up under perspective, which is
    // what pushed the slab out of the riser at high values.
    //
    // Kept shallow: the rotation foreshortens the slab's painted height while
    // its layout box keeps the full column, so a steep angle reads as a large
    // empty strip above the pedal.
    get tilt() { return 16 - this.value * 0.16; },
    get fillHeight() { return `${this.value}%`; },
    get slabStyle() {
      // transform-origin at the bottom: the pedal hinges on its heel, so the
      // toe swings and the footprint never grows past the box.
      return `transform: rotateX(${this.tilt}deg)`;
    },

    apply(ev) {
      const r = this.$refs.slab.getBoundingClientRect();
      const f = 1 - (ev.clientY - r.top) / r.height;
      store().set("wah_position", Math.round(Math.min(100, Math.max(0, f * 100))));
    },
    down(ev) {
      ev.target.setPointerCapture?.(ev.pointerId);
      this.dragging = true;
      store().hold("wah_position", true);
      this.apply(ev);
    },
    move(ev) {
      if (!this.dragging) return;
      this.apply(ev);
    },
    up(ev) {
      ev.target.releasePointerCapture?.(ev.pointerId);
      this.dragging = false;
      store().hold("wah_position", false);
    },
    key(ev) {
      const map = { ArrowUp: 1, ArrowRight: 1, ArrowDown: -1, ArrowLeft: -1, PageUp: 10, PageDown: -10 };
      const d = map[ev.key];
      if (d === undefined) return;
      ev.preventDefault();
      store().set("wah_position", Math.min(100, Math.max(0, this.value + d)));
    },
  };
}

/** Draw-anywhere graphic EQ: drag across the pad and the bands follow. */
export function eqPad() {
  return {
    bands: EQ_BANDS,
    dragging: false,
    hover: null,
    _lastIdx: null,

    // The dock sits over the pedalboard on a 9-inch panel, so it starts
    // collapsed to a curve and remembers the choice for this browser.
    expanded: localStorage.getItem("katana.eq.expanded") === "1",
    toggleExpanded() {
      this.expanded = !this.expanded;
      try { localStorage.setItem("katana.eq.expanded", this.expanded ? "1" : "0"); } catch {}
    },

    get values() {
      const out = {};
      for (const b of EQ_BANDS) out[b.key] = store().num(b.key);
      return out;
    },
    get on() { return store().bool("eq_switch"); },
    get curve() { return eqPath(this.values, 50); },
    get fill() { return `${this.curve} L 100 100 L 0 100 Z`; },
    points() {
      return EQ_BANDS.map((b, i) => ({
        key: b.key, label: b.label, v: this.values[b.key] ?? 0,
        x: (i / (EQ_N - 1)) * 100,
        y: 50 - ((this.values[b.key] ?? 0) / EQ_RANGE) * 50,
      }));
    },

    apply(ev) {
      const r = this.$refs.pad.getBoundingClientRect();
      const { idx, value } = eqHit(r, ev.clientX, ev.clientY);
      // fill the gap when the finger moves fast
      for (const g of eqGapFill(this._lastIdx, idx, value, this.values)) {
        store().set(g.key, g.value);
      }
      this._lastIdx = idx;
      this.hover = idx;
      store().set(EQ_BANDS[idx].key, value);
    },
    down(ev) {
      ev.target.setPointerCapture?.(ev.pointerId);
      this._lastIdx = null;
      this.dragging = true;
      // Drawing sweeps across bands, so hold the whole row until the
      // gesture ends rather than one band at a time.
      EQ_BANDS.forEach((b) => store().hold(b.key, true));
      this.apply(ev);
    },
    move(ev) {
      if (!this.dragging) return;
      this.apply(ev);
    },
    up(ev) {
      ev.target.releasePointerCapture?.(ev.pointerId);
      this.dragging = false;
      this.hover = null;
      this._lastIdx = null;
      EQ_BANDS.forEach((b) => store().hold(b.key, false));
    },
    flat() {
      EQ_BANDS.forEach((b) => store().set(b.key, 0));
    },
  };
}

/** The custom wah gesture: N sweeps of low..high, `seconds` each.
 *  Settings persist per browser - this is a per-player feel thing, and
 *  retyping four numbers before every take would make it unusable. */
export function wahRock() {
  const saved = (() => {
    try { return JSON.parse(localStorage.getItem("katana.rock") || "{}"); }
    catch { return {}; }
  })();

  return {
    open: false,
    running: false,
    error: null,
    intervals: saved.intervals ?? 4,
    low: saved.low ?? 0,
    high: saved.high ?? 50,
    seconds: saved.seconds ?? 2.3,
    bounce: saved.bounce ?? true,

    get total() { return (this.intervals * this.seconds).toFixed(1); },
    get summary() {
      return `${this.intervals} × ${this.low}\u2192${this.high} @ ${this.seconds}s`;
    },
    /** Mirrors the server's guards, so a bad value is caught before the
     *  request rather than coming back as a 422. */
    get invalid() {
      if (this.low === this.high) return "low and high must differ";
      if (this.intervals < 1 || this.intervals > 32) return "1-32 intervals";
      if (this.seconds < 0.05 || this.seconds > 30) return "0.05-30 s";
      if (this.intervals * this.seconds > 120) return "total must be under 120 s";
      return null;
    },

    persist() {
      try {
        localStorage.setItem("katana.rock", JSON.stringify({
          intervals: this.intervals, low: this.low, high: this.high,
          seconds: this.seconds, bounce: this.bounce,
        }));
      } catch {}
    },

    async run() {
      if (this.invalid || this.running) return;
      this.persist();
      this.error = null;
      this.running = true;
      // The gesture runs for seconds and holds the amp lock; show it as busy
      // so the surface does not look frozen and nothing else is sent.
      try {
        await Alpine.store("katana").runBusy(
          `wah ${this.summary}`,
          () => transport.rockWah({
            intervals: this.intervals, low: this.low, high: this.high,
            seconds: this.seconds, bounce: this.bounce,
          }),
        );
      } catch (e) {
        this.error = String(e.message ?? e);
      } finally {
        this.running = false;
      }
    },
  };
}

/** Channel rail with press-and-hold to overwrite a stored patch. */
export function channelRail() {
  return {
    pending: null,
    _timer: null,

    holdStart(id) {
      this._timer = setTimeout(() => { this.pending = id; }, 650);
    },
    holdEnd() {
      if (this._timer) clearTimeout(this._timer);
      this._timer = null;
    },
    confirm() {
      const id = this.pending;
      this.pending = null;
      if (id) store().saveToChannel(id);
    },
  };
}
