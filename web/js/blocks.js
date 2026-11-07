// Which parameters each editor panel shows.
// Ranges, step text and the FX-slot knobs all come from schema.js (the
// amp's own tables, in param.py and effects.py); the labels, ordering and
// grouping of the fixed panels are interface decisions and live here.

import { PARAMS, PARAM_BY_KEY } from "./schema.js";

export const BLOCK_TITLES = {
  amp: "Amp setup",
  boost: "Boost / Overdrive",
  mod: "Mod — FX slot 1",
  fx: "FX — slot 2",
  delay: "Delay",
  reverb: "Reverb",
  gate: "Noise gate",
  eq: "EQ",
  wah: "Pedal FX",
};

/** The knobs of whichever effect slot 1 or 2 is set to, in the amp's order.
 *  Empty for a TYPE number the amp accepts but no effect uses. */
export function effectParams(slot, type) {
  return PARAMS
    .filter((param) => param.slot === slot && param.effect === type)
    .map((param) => ({ key: param.key, label: param.label }));
}

// The Harmonist's key is one setting shared by both slots, not a slot knob.
export const HARMONIST_TYPE = 16;
export const MASTER_KEY = { key: "master_key", label: "Key" };

export const AMP_PARAMS = [
  { key: "cabinet_resonance", label: "Cabinet" },
  { key: "solo_switch", label: "Solo" },
  { key: "solo_level", label: "Solo Lvl" },
  { key: "contour_switch", label: "Contour" },
  { key: "contour_select", label: "Active contour" },
  { key: "send_return_switch", label: "FX Loop" },
  { key: "send_return_mode", label: "Loop Mode" },
  { key: "send_return_position", label: "Loop Position" },
  { key: "send_return_send_level", label: "Send" },
  { key: "send_return_return_level", label: "Return" },
];

/** The settings of the selected contour (1-3), for the amp panel. */
export const contourParams = (number) => [
  { key: `contour${number}_type`, label: `C${number} Type` },
  { key: `contour${number}_freq_shift`, label: `C${number} Freq` },
];

export const BOOST_PARAMS = [
  { key: "boost_type", label: "Pedal" },
  { key: "boost_drive", label: "Drive" },
  { key: "boost_bottom", label: "Bottom" },
  { key: "boost_tone", label: "Tone" },
  { key: "boost_level", label: "Level" },
  { key: "boost_direct_mix", label: "Direct" },
  { key: "boost_solo_level", label: "Solo Lvl" },
  { key: "boost_solo_switch", label: "Solo" }
];

export const REVERB_SPRING = 5;
export const reverbParams = (type) => [
  { key: "reverb_type", label: "Type" },
  { key: "reverb_time", label: "Time" },
  { key: "reverb_pre_delay", label: "Pre-Dly" },
  { key: "reverb_low_cut", label: "Low Cut" },
  { key: "reverb_high_cut", label: "High Cut" },
  { key: "reverb_density", label: "Density" },
  { key: "reverb_level", label: "Level" },
  { key: "reverb_direct_mix", label: "Direct" },
  ...(type === REVERB_SPRING ? [{ key: "reverb_spring_color", label: "Color" }] : []),
];

// pedal_type: each mode keeps its own settings, so show only the active one's.
// The treadle position itself is driven by the treadle control, not a knob.
const PEDAL_MODE_PARAMS = {
  0: [
    { key: "wah_type", label: "Voicing" },
    { key: "wah_pedal_min", label: "Pedal Min" },
    { key: "wah_pedal_max", label: "Pedal Max" },
    { key: "wah_level", label: "Level" },
    { key: "wah_direct_mix", label: "Direct" },
  ],
  1: [
    { key: "pedal_bend_pitch", label: "Pitch" },
    { key: "pedal_bend_level", label: "Level" },
    { key: "pedal_bend_direct_mix", label: "Direct" },
  ],
  2: [
    { key: "wah_95e_pedal_min", label: "Pedal Min" },
    { key: "wah_95e_pedal_max", label: "Pedal Max" },
    { key: "wah_95e_level", label: "Level" },
    { key: "wah_95e_direct_mix", label: "Direct" },
  ],
};
export const wahParams = (pedalType) => [
  { key: "pedal_type", label: "Mode" },
  { key: "pedal_position", label: "Position" },
  ...(PEDAL_MODE_PARAMS[pedalType] ?? []),
  { key: "foot_volume", label: "Foot Vol" },
];

export const GATE_PARAMS = [
  { key: "noise_suppressor_threshold", label: "Threshold" },
  { key: "noise_suppressor_release", label: "Release" }
];

// EQ: one block, two types. 0 = parametric, 1 = GE-10 (the ten bands, which
// have their own pad on the main screen).
export const eqParams = (type) => [
  { key: "eq_type", label: "Type" },
  { key: "eq_position", label: "Position" },
  ...(type === 0 ? [
    { key: "eq_low_cut", label: "Low Cut" },
    { key: "eq_low_gain", label: "Low" },
    { key: "eq_low_mid_freq", label: "Lo-Mid Freq" },
    { key: "eq_low_mid_q", label: "Lo-Mid Q" },
    { key: "eq_low_mid_gain", label: "Lo-Mid" },
    { key: "eq_high_mid_freq", label: "Hi-Mid Freq" },
    { key: "eq_high_mid_q", label: "Hi-Mid Q" },
    { key: "eq_high_mid_gain", label: "Hi-Mid" },
    { key: "eq_high_gain", label: "High" },
    { key: "eq_high_cut", label: "High Cut" },
    { key: "eq_peq_level", label: "Level" },
  ] : [
    { key: "eq_level", label: "EQ Level" },
  ]),
];

// Delay types with settings of their own (values of delay_type).
const DELAY_PAN = 1, DELAY_MODULATE = 9, DELAY_SDE_3000 = 10;
export const delayParams = (prefix, type) => [
  { key: `${prefix}_type`, label: "Type" },
  { key: `${prefix}_time`, label: "Time", unit: "ms" },
  { key: `${prefix}_feedback`, label: "Feedback" },
  { key: `${prefix}_high_cut`, label: "High Cut" },
  { key: `${prefix}_level`, label: "Level" },
  { key: `${prefix}_direct_mix`, label: "Direct" },
  ...(type === DELAY_PAN ? [{ key: `${prefix}_tap_time`, label: "Tap" }] : []),
  ...(type === DELAY_MODULATE || type === DELAY_SDE_3000 ? [
    { key: `${prefix}_mod_rate`, label: "Mod Rate" },
    { key: `${prefix}_mod_depth`, label: "Mod Depth" },
  ] : []),
  ...(type === DELAY_SDE_3000 ? [
    { key: `${prefix}_sde_range`, label: "Range" },
    { key: `${prefix}_sde_feedback_phase`, label: "Fb Phase" },
    { key: `${prefix}_sde_delay_phase`, label: "Dly Phase" },
    { key: `${prefix}_sde_filter`, label: "Filter" },
    { key: `${prefix}_sde_mod_switch`, label: "Mod" },
  ] : []),
];

/** Merge a display label with the amp's real range/kind. */
export function resolve(display) {
  const param = PARAM_BY_KEY[display.key];
  if (!param) throw new Error(`Unknown parameter ${display.key} - not in param.py`);
  return {
    key: display.key,
    label: display.label,
    kind: param.kind,
    min: param.min ?? 0,
    max: param.max ?? 100,
    unit: display.unit ?? param.unit ?? "",
    options: param.options ?? [],
    readOnly: param.readOnly,
  };
}

/** Only the continuous ones get a knob. */
export function knobParams(params) {
  return params.map(resolve).filter((param) => param.kind === "range");
}
export function enumParams(params) {
  return params.map(resolve).filter((param) => param.kind === "enum");
}
export function toggleParams(params) {
  return params.map(resolve).filter((param) => param.kind === "toggle");
}

/** A whole panel's worth: { enums, knobs, toggles } from one list. */
export function panel(params, note = null) {
  return { enums: enumParams(params), knobs: knobParams(params), toggles: toggleParams(params), note };
}
