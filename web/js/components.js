// Alpine component factories.
//
// Each returns an x-data object. Templates live in index.html; these hold
// only the behaviour and the derived geometry, so the markup stays readable.

import {
  dragValue, knobArc, knobAngle, KNOB_START, KNOB_SWEEP, KNOB_SIZES,
  eqPath, eqHit, eqGapFill,
  peqPath, peqX, peqY, stepHertz, PEQ_F_MIN, PEQ_F_MAX, PEQ_RANGE, PEQ_GAIN_LIMIT,
  PEQ_TICKS, LOW_SHELF_HZ, HIGH_SHELF_HZ,
} from "./controls.js";
import { EQ_BANDS, AMP_MODEL_OPTIONS, PARAM_BY_KEY } from "./schema.js";
import { transport } from "./transport.js";

const store = () => Alpine.store("katana");

/** One amp knob. `key` is the parameter; pass `disabled` for a read-only one.
 *  Range, unit and step text come from the schema unless passed in. */
export function knob(key, label, { accent = "steel", size = "md", min, max, unit, disabled = false } = {}) {
  const param = PARAM_BY_KEY[key] ?? {};
  min = min ?? param.min ?? 0;
  max = max ?? param.max ?? 100;
  unit = unit ?? param.unit ?? "";
  const steps = param.steps ?? null;
  return {
    key, label, accent, size, min, max, unit, disabled,
    sizePx: KNOB_SIZES[size],
    trackPath: knobArc(KNOB_START, KNOB_START + KNOB_SWEEP),
    capId: `cap-${key}`,

    get value() { return store().num(this.key); },
    get angle() { return knobAngle(this.value, this.min, this.max); },
    get valuePath() { return knobArc(KNOB_START, this.angle + 0.01); },
    // A stepped knob shows Tone Studio's text ("1.25 kHz"), not the step number.
    get readout() {
      const value = Math.round(this.value);
      return steps ? (steps[value - this.min] ?? String(value)) : `${value}${this.unit}`;
    },

    drag: null,
    init() {
      const self = this;
      this.drag = dragValue({
        min, max,
        travel: 200,
        holdKey: key,
        hold: (key, holding) => store().hold(key, holding),
        get: () => store().num(self.key),
        set: (value) => store().set(self.key, value),
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
      const index = this.options.findIndex((option) => option.value === this.value);
      return Math.max(0, index);
    },
    get name() {
      return this.options.find((option) => option.value === this.value)?.label ?? "—";
    },
    get pointerAngle() { return (this.index / this.options.length) * 360; },
    orbitStyle(mark) {
      const rad = ((mark.angle - 90) * Math.PI) / 180;
      const left = 50 + 38 * Math.cos(rad);
      const top = 50 + 38 * Math.sin(rad);
      return `left:${left}%;top:${top}%;transform:translate(-50%,-50%)`;
    },

    drag: null,
    init() {
      const self = this;
      this.drag = dragValue({
        min: 0,
        max: AMP_MODEL_OPTIONS.length - 1,
        travel: 260,
        holdKey: "amp_type",
        hold: (key, holding) => store().hold(key, holding),
        get: () => self.index,
        set: (index) => {
          const value = AMP_MODEL_OPTIONS[index]?.value;
          if (value !== undefined) store().set("amp_type", value);
        },
      });
    },
  };
}

/** The wah treadle: the whole slab is the pedal. */
// pedal_type -> the settings the treadle moves. Each pedal mode keeps its
// own position (and the two wahs their own travel limits).
const PEDAL_MODES = {
  0: { position: "wah_position", min: "wah_pedal_min", max: "wah_pedal_max" },
  1: { position: "pedal_bend_position", min: null, max: null },
  2: { position: "wah_95e_position", min: "wah_95e_pedal_min", max: "wah_95e_pedal_max" },
};

export function treadle() {
  return {
    dragging: false,

    get mode() { return PEDAL_MODES[store().num("pedal_type")] ?? PEDAL_MODES[0]; },
    get value() { return store().num(this.mode.position); },
    get min() { return this.mode.min ? store().num(this.mode.min) : 0; },
    get max() { return this.mode.max ? store().num(this.mode.max) : 100; },
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
      const rect = this.$refs.slab.getBoundingClientRect();
      const fraction = 1 - (ev.clientY - rect.top) / rect.height;
      store().set(this.mode.position, Math.round(Math.min(100, Math.max(0, fraction * 100))));
    },
    down(ev) {
      ev.target.setPointerCapture?.(ev.pointerId);
      this.dragging = true;
      store().hold(this.mode.position, true);
      this.apply(ev);
    },
    move(ev) {
      if (!this.dragging) return;
      this.apply(ev);
    },
    up(ev) {
      ev.target.releasePointerCapture?.(ev.pointerId);
      this.dragging = false;
      store().hold(this.mode.position, false);
    },
    key(ev) {
      const map = { ArrowUp: 1, ArrowRight: 1, ArrowDown: -1, ArrowLeft: -1, PageUp: 10, PageDown: -10 };
      const step = map[ev.key];
      if (step === undefined) return;
      ev.preventDefault();
      store().set(this.mode.position, Math.min(100, Math.max(0, this.value + step)));
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
      for (const band of EQ_BANDS) out[band.key] = store().num(band.key);
      return out;
    },
    get on() { return store().bool("eq_switch"); },
    // eq_type 0 is the parametric EQ, 1 the GE-10. The amp keeps both.
    get parametric() { return store().num("eq_type") === 0; },
    toggleType() { store().set("eq_type", this.parametric ? 1 : 0); },
    get curve() { return this.parametric ? peqPath(peqSettings()) : eqPath(this.values, 50); },
    get fill() { return `${this.curve} L 100 100 L 0 100 Z`; },

    // ---- parametric: draggable dots ----
    ticks: PEQ_TICKS,
    selected: null,
    _node: null,
    get nodes() {
      return PEQ_NODES.map((node) => ({ ...node, ...nodePosition(node), active: node.id === this.selected }));
    },
    get selectedNode() { return PEQ_NODES.find((node) => node.id === this.selected) ?? null; },
    get readout() {
      const node = this.selectedNode;
      return node ? nodeReadout(node) : "drag a dot · tap a mid dot for Q";
    },
    get level() {
      const value = store().num("eq_peq_level");
      return `level ${value > 0 ? "+" : ""}${value} dB`;
    },
    nudgeQ(step) {
      const node = this.selectedNode;
      if (!node?.q) return;
      const steps = PARAM_BY_KEY[node.q].steps;
      store().set(node.q, Math.min(steps.length - 1, Math.max(0, store().num(node.q) + step)));
    },
    /** The dot nearest the pointer, if one is close enough to grab. */
    _grab(ev) {
      const rect = this.$refs.pad.getBoundingClientRect();
      let best = null, bestDistance = 28;
      for (const node of PEQ_NODES) {
        const { x, y } = nodePosition(node);
        const distance = Math.hypot(ev.clientX - rect.left - (x / 100) * rect.width, ev.clientY - rect.top - (y / 100) * rect.height);
        if (distance < bestDistance) { best = node; bestDistance = distance; }
      }
      return best;
    },
    _drag(ev) {
      const node = this._node;
      const rect = this.$refs.pad.getBoundingClientRect();
      const across = Math.min(100, Math.max(0, ((ev.clientX - rect.left) / rect.width) * 100));
      const down = Math.min(1, Math.max(0, (ev.clientY - rect.top) / rect.height));
      if (node.freq) {
        // Snap to the nearest step the amp offers.
        const steps = PARAM_BY_KEY[node.freq].steps;
        let nearest = 0;
        steps.forEach((label, index) => {
          if (Math.abs(peqX(stepHertz(label, node.flat)) - across) < Math.abs(peqX(stepHertz(steps[nearest], node.flat)) - across)) nearest = index;
        });
        store().set(node.freq, nearest);
      }
      if (node.gain) {
        const gain = Math.round((0.5 - down) * 2 * PEQ_RANGE);
        store().set(node.gain, Math.min(PEQ_GAIN_LIMIT, Math.max(-PEQ_GAIN_LIMIT, gain)));
      }
    },
    wheel(ev) {
      if (!this.parametric) return;
      const node = this._grab(ev) ?? this.selectedNode;
      if (!node?.q) return;
      ev.preventDefault();
      this.selected = node.id;
      this.nudgeQ(ev.deltaY < 0 ? 1 : -1);
    },

    down(ev) {
      if (this.parametric) {
        const node = this._grab(ev);
        this.selected = node?.id ?? null;
        if (!node) return;
        ev.target.setPointerCapture?.(ev.pointerId);
        this._node = node;
        this.dragging = true;
        nodeKeys(node).forEach((key) => store().hold(key, true));
        return;
      }
      ev.target.setPointerCapture?.(ev.pointerId);
      this._lastIdx = null;
      this.dragging = true;
      // Drawing sweeps across bands, so hold the whole row until the
      // gesture ends rather than one band at a time.
      EQ_BANDS.forEach((band) => store().hold(band.key, true));
      this.apply(ev);
    },
    move(ev) {
      if (!this.dragging) return;
      if (this._node) this._drag(ev);
      else this.apply(ev);
    },
    up(ev) {
      ev.target.releasePointerCapture?.(ev.pointerId);
      this.dragging = false;
      if (this._node) {
        nodeKeys(this._node).forEach((key) => store().hold(key, false));
        this._node = null;
        return;
      }
      this.hover = null;
      this._lastIdx = null;
      EQ_BANDS.forEach((band) => store().hold(band.key, false));
    },
    flat() {
      if (this.parametric) {
        // Cuts open, every gain to 0. Frequencies, Q and level stay put.
        store().set("eq_low_cut", 0);
        store().set("eq_high_cut", PARAM_BY_KEY.eq_high_cut.steps.length - 1);
        PEQ_NODES.forEach((node) => node.gain && store().set(node.gain, 0));
        return;
      }
      EQ_BANDS.forEach((band) => store().set(band.key, 0));
    },

    apply(ev) {
      const rect = this.$refs.pad.getBoundingClientRect();
      const { idx, value } = eqHit(rect, ev.clientX, ev.clientY);
      // fill the gap when the finger moves fast
      for (const fill of eqGapFill(this._lastIdx, idx, value, this.values)) {
        store().set(fill.key, fill.value);
      }
      this._lastIdx = idx;
      this.hover = idx;
      store().set(EQ_BANDS[idx].key, value);
    },
  };
}

// ---- parametric EQ helpers ----
//
// One dot per band. `freq` moves it left/right through the amp's steps,
// `gain` moves it up/down, `q` is its width. The shelves sit at a fixed,
// assumed frequency; the cuts stay on the centre line.
const PEQ_NODES = [
  { id: "low_cut", label: "Low Cut", freq: "eq_low_cut", flat: PEQ_F_MIN },
  { id: "low", label: "Low", gain: "eq_low_gain", hertz: LOW_SHELF_HZ },
  { id: "low_mid", label: "Lo-Mid", freq: "eq_low_mid_freq", q: "eq_low_mid_q", gain: "eq_low_mid_gain" },
  { id: "high_mid", label: "Hi-Mid", freq: "eq_high_mid_freq", q: "eq_high_mid_q", gain: "eq_high_mid_gain" },
  { id: "high", label: "High", gain: "eq_high_gain", hertz: HIGH_SHELF_HZ },
  { id: "high_cut", label: "High Cut", freq: "eq_high_cut", flat: PEQ_F_MAX },
];

const stepLabel = (key) => PARAM_BY_KEY[key].steps[store().num(key)] ?? "";
const nodeHertz = (node) => (node.freq ? stepHertz(stepLabel(node.freq), node.flat) : node.hertz);
const nodeKeys = (node) => [node.freq, node.gain].filter(Boolean);

function nodePosition(node) {
  return { x: peqX(nodeHertz(node)), y: peqY(node.gain ? store().num(node.gain) : 0) };
}

function nodeReadout(node) {
  const parts = [node.label];
  if (node.freq) parts.push(stepLabel(node.freq));
  if (node.q) parts.push(`Q ${stepLabel(node.q)}`);
  if (node.gain) {
    const gain = store().num(node.gain);
    parts.push(`${gain > 0 ? "+" : ""}${gain} dB`);
  }
  return parts.join(" · ");
}

/** The amp's parametric settings, in the units the curve math wants. */
function peqSettings() {
  const cut = (key, flat) => (stepLabel(key) === "FLAT" ? null : stepHertz(stepLabel(key), flat));
  const mid = (prefix) => ({
    hertz: stepHertz(stepLabel(`${prefix}_freq`)),
    q: parseFloat(stepLabel(`${prefix}_q`)) || 1,
    gain: store().num(`${prefix}_gain`),
  });
  return {
    lowCut: cut("eq_low_cut", PEQ_F_MIN),
    highCut: cut("eq_high_cut", PEQ_F_MAX),
    lowGain: store().num("eq_low_gain"),
    highGain: store().num("eq_high_gain"),
    mids: [mid("eq_low_mid"), mid("eq_high_mid")],
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
