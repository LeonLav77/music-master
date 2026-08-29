// Pointer interactions and the geometry the SVG controls draw from.
//
// This is the part that carried the most risk in the port: pointer capture,
// axis mapping, snapping and the EQ gap-fill all had to keep behaving the
// same on the panel's touchscreen.

import { EQ_BANDS } from "./schema.js";

/** Pointer drag -> value. Works with mouse, pen and touch.
 *
 *  Returns handlers to spread onto an element via x-on. `opts` is read
 *  lazily through getters so the current value is always the live one -
 *  Alpine has no dependency array to re-close over. */
export function dragValue(opts) {
  const start = { p: 0, v: 0 };
  const axis = opts.axis ?? "y";
  const travel = opts.travel ?? 220;
  const step = opts.step ?? 1;

  return {
    down(ev) {
      ev.target.setPointerCapture?.(ev.pointerId);
      start.p = axis === "y" ? ev.clientY : ev.clientX;
      start.v = opts.get();
      if (opts.holdKey) opts.hold(opts.holdKey, true);
    },
    move(ev) {
      if (!ev.target.hasPointerCapture?.(ev.pointerId)) return;
      const cur = axis === "y" ? ev.clientY : ev.clientX;
      const delta = axis === "y" ? start.p - cur : cur - start.p;
      const raw = start.v + (delta / travel) * (opts.max - opts.min);
      const snapped = Math.round(raw / step) * step;
      const next = Math.min(opts.max, Math.max(opts.min, snapped));
      if (next !== opts.get()) opts.set(next);
    },
    up(ev) {
      ev.target.releasePointerCapture?.(ev.pointerId);
      if (opts.holdKey) opts.hold(opts.holdKey, false);
    },
    key(ev) {
      const big = (opts.max - opts.min) / 10;
      const map = {
        ArrowUp: step, ArrowRight: step,
        ArrowDown: -step, ArrowLeft: -step,
        PageUp: big, PageDown: -big,
      };
      const d = map[ev.key];
      if (d === undefined) return;
      ev.preventDefault();
      opts.set(Math.min(opts.max, Math.max(opts.min, Math.round(opts.get() + d))));
    },
  };
}

// ---- knob geometry ----

export const KNOB_START = -135;
export const KNOB_SWEEP = 270;
const KNOB_R = 44;

/** SVG arc path on the knob's track circle. */
export function knobArc(from, to) {
  const rad = (a) => ((a - 90) * Math.PI) / 180;
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
  lg: "clamp(128px, 9vw, 168px)",
};

/** The 24 tick marks around the cap. */
export const KNOB_TICKS = Array.from({ length: 24 }, (_, i) => i * 15);

// ---- EQ pad ----

export const EQ_N = EQ_BANDS.length;
export const EQ_RANGE = 24;

/** Polyline path for a set of band values. `spread` is the vertical share of
 *  the viewBox the full range uses (the mini curve is flatter than the pad). */
export function eqPath(values, spread = 50) {
  return EQ_BANDS.map((b, i) => {
    const v = values[b.key] ?? 0;
    const x = (i / (EQ_N - 1)) * 100;
    const y = 50 - (v / EQ_RANGE) * spread;
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
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
  for (let i = prev + step; i !== idx; i += step) {
    const t = (i - prev) / (idx - prev);
    out.push({ key: EQ_BANDS[i].key, value: Math.round(from + (clamped - from) * t) });
  }
  return out;
}
