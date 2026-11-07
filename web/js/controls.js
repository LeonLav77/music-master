// Pointer interactions and the geometry the SVG controls draw from.
//

import { EQ_BANDS } from "./schema.js";

/** Pointer drag -> value. Works with mouse, pen and touch.
 *
 *  Returns handlers to spread onto an element via x-on. `opts` is read
 *  lazily through getters so the current value is always the live one -
 *  Alpine has no dependency array to re-close over. */
export function dragValue(opts) {
  // Vertical: drag up to turn up, `travel` pixels for the full range.
  const start = { y: 0, v: 0 };
  const travel = opts.travel ?? 220;

  return {
    down(ev) {
      ev.target.setPointerCapture?.(ev.pointerId);
      start.y = ev.clientY;
      start.v = opts.get();
      if (opts.holdKey) opts.hold(opts.holdKey, true);
    },
    move(ev) {
      if (!ev.target.hasPointerCapture?.(ev.pointerId)) return;
      const delta = start.y - ev.clientY;
      const raw = start.v + (delta / travel) * (opts.max - opts.min);
      const next = Math.min(opts.max, Math.max(opts.min, Math.round(raw)));
      if (next !== opts.get()) opts.set(next);
    },
    up(ev) {
      ev.target.releasePointerCapture?.(ev.pointerId);
      if (opts.holdKey) opts.hold(opts.holdKey, false);
    },
    key(ev) {
      const big = (opts.max - opts.min) / 10;
      const map = {
        ArrowUp: 1, ArrowRight: 1,
        ArrowDown: -1, ArrowLeft: -1,
        PageUp: big, PageDown: -big,
      };
      const step = map[ev.key];
      if (step === undefined) return;
      ev.preventDefault();
      opts.set(Math.min(opts.max, Math.max(opts.min, Math.round(opts.get() + step))));
    },
  };
}

// ---- knob geometry ----

export const KNOB_START = -135;
export const KNOB_SWEEP = 270;
const KNOB_R = 44;

/** SVG arc path on the knob's track circle. */
export function knobArc(from, to) {
  const rad = (angle) => ((angle - 90) * Math.PI) / 180;
  const x1 = 50 + KNOB_R * Math.cos(rad(from));
  const y1 = 50 + KNOB_R * Math.sin(rad(from));
  const x2 = 50 + KNOB_R * Math.cos(rad(to));
  const y2 = 50 + KNOB_R * Math.sin(rad(to));
  return `M ${x1} ${y1} A ${KNOB_R} ${KNOB_R} 0 ${to - from > 180 ? 1 : 0} 1 ${x2} ${y2}`;
}

/** Pointer angle for a value within [min,max]. */
export function knobAngle(value, min, max) {
  const pct = max === min ? 0 : (value - min) / (max - min);
  return KNOB_START + pct * KNOB_SWEEP;
}

export const KNOB_SIZES = {
  sm: "clamp(60px, 5.6vw, 104px)",
  md: "clamp(96px, 7.4vw, 136px)",
};

// ---- EQ pad ----

export const EQ_N = EQ_BANDS.length;
export const EQ_RANGE = 24;

/** Polyline path for a set of band values. `spread` is the vertical share of
 *  the viewBox the full range uses (the mini curve is flatter than the pad). */
export function eqPath(values, spread = 50) {
  return EQ_BANDS.map((band, index) => {
    const value = values[band.key] ?? 0;
    const across = (index / (EQ_N - 1)) * 100;
    const height = 50 - (value / EQ_RANGE) * spread;
    return `${index === 0 ? "M" : "L"} ${across} ${height}`;
  }).join(" ");
}

/** Which band a pointer is over, and the value it implies. */
export function eqHit(rect, clientX, clientY) {
  const fx = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
  const fy = Math.min(1, Math.max(0, (clientY - rect.top) / rect.height));
  const idx = Math.round(fx * (EQ_N - 1));
  const val = Math.round((0.5 - fy) * 2 * EQ_RANGE);
  return { idx, value: Math.min(EQ_RANGE, Math.max(-EQ_RANGE, val)) };
}

/** Bands to write when the finger jumps several bands in one move.
 *  Without this a fast sweep leaves untouched gaps behind it. */
export function eqGapFill(prev, idx, clamped, values) {
  const out = [];
  if (prev === null || Math.abs(idx - prev) <= 1) return out;
  const from = values[EQ_BANDS[prev].key] ?? 0;
  const step = idx > prev ? 1 : -1;
  for (let band = prev + step; band !== idx; band += step) {
    const progress = (band - prev) / (idx - prev);
    out.push({ key: EQ_BANDS[band].key, value: Math.round(from + (clamped - from) * progress) });
  }
  return out;
}

// ---- parametric EQ ----
//
// The parametric pad draws the curve the settings produce, on a log
// frequency axis. The axis ends sit just outside the amp's real range, so
// the two cut filters' FLAT setting gets a spot of its own at each edge.

export const PEQ_F_MIN = 14;
export const PEQ_F_MAX = 20000;
export const PEQ_RANGE = 24;   // dB from the centre line to the edge, as on the GE-10 pad
export const PEQ_GAIN_LIMIT = 20;
// Roland does not publish where the Low/High shelves start to bend, so the
// drawn curve assumes these. The values sent to the amp are exact either way.
export const LOW_SHELF_HZ = 100;
export const HIGH_SHELF_HZ = 8000;

/** Horizontal position (0-100) of a frequency. */
export function peqX(hertz) {
  return (Math.log(hertz / PEQ_F_MIN) / Math.log(PEQ_F_MAX / PEQ_F_MIN)) * 100;
}

/** Vertical position (0-100, top is +) of a level in dB. */
export function peqY(decibels) {
  return 50 - (decibels / PEQ_RANGE) * 50;
}

/** A step label as hertz: "1.25 kHz" -> 1250. FLAT has no frequency, so it
 *  takes `flat` - the axis edge it is drawn at. */
export function stepHertz(label, flat) {
  if (label === "FLAT") return flat;
  const number = parseFloat(label);
  return label.includes("kHz") ? number * 1000 : number;
}

// Each filter's power gain (|H|^2) at one frequency, from the textbook
// analog shapes. Multiplying them stacks the filters, like the amp does.
function cutPower(hertz, corner, highPass) {
  const ratio = (hertz / corner) ** 4;          // 24 dB per octave
  return highPass ? ratio / (1 + ratio) : 1 / (1 + ratio);
}

function shelfPower(hertz, corner, gain, low) {
  const amplitude = 10 ** (gain / 20);
  const ratio = (hertz / corner) ** 2;
  return low
    ? (ratio + amplitude ** 2) / (ratio + 1)
    : (amplitude ** 2 * ratio + 1) / (ratio + 1);
}

function peakPower(hertz, centre, width, gain) {
  const amplitude = 10 ** (gain / 40);
  const ratio = hertz / centre;
  const detune = (1 - ratio ** 2) ** 2;
  return (detune + (ratio * amplitude / width) ** 2) / (detune + (ratio / (amplitude * width)) ** 2);
}

/** The EQ's effect in dB at one frequency. `settings` is
 *  { lowCut, highCut (hertz or null for FLAT), lowGain, highGain, mids: [{ hertz, q, gain }] }. */
export function peqResponse(settings, hertz) {
  let power = shelfPower(hertz, LOW_SHELF_HZ, settings.lowGain, true)
    * shelfPower(hertz, HIGH_SHELF_HZ, settings.highGain, false);
  if (settings.lowCut) power *= cutPower(hertz, settings.lowCut, true);
  if (settings.highCut) power *= cutPower(hertz, settings.highCut, false);
  for (const band of settings.mids) power *= peakPower(hertz, band.hertz, band.q, band.gain);
  return 10 * Math.log10(power);
}

/** SVG path of the whole curve, sampled across the axis. */
export function peqPath(settings, points = 120) {
  const parts = [];
  for (let index = 0; index <= points; index++) {
    const across = (index / points) * 100;
    const hertz = PEQ_F_MIN * (PEQ_F_MAX / PEQ_F_MIN) ** (across / 100);
    const height = Math.min(100, Math.max(0, peqY(peqResponse(settings, hertz))));
    parts.push(`${index === 0 ? "M" : "L"} ${across.toFixed(2)} ${height.toFixed(2)}`);
  }
  return parts.join(" ");
}

/** Frequency ticks for the axis under the pad. */
export const PEQ_TICKS = [
  { hertz: 50, label: "50" }, { hertz: 100, label: "100" }, { hertz: 200, label: "200" },
  { hertz: 500, label: "500" }, { hertz: 1000, label: "1k" }, { hertz: 2000, label: "2k" },
  { hertz: 5000, label: "5k" }, { hertz: 10000, label: "10k" },
].map((tick) => ({ ...tick, x: peqX(tick.hertz) }));
