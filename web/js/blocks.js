// Which parameters each editor panel shows.
// Ranges come from schema.js (the amp's own tables); the labels, ordering
// and grouping are interface decisions and live here.

import { PARAM_BY_KEY } from "./schema.js";

export const BLOCK_TITLES = {
  boost: "Boost / Overdrive",
  mod: "Mod \u2014 FX slot 1",
  fx: "FX \u2014 slot 2",
  delay: "Delay engines",
  reverb: "Reverb",
  gate: "Noise gate",
  eq: "Graphic EQ",
  wah: "Wah / Expression",
};

/** Effects whose knobs are mapped. Anything else renders a "not mapped" notice. */
export const FX_PARAM_MAP = {
  "Auto Wah": [
    { key: "auto_wah_rate", label: "Rate" },
    { key: "auto_wah_depth", label: "Depth" },
    { key: "auto_wah_frequency", label: "Freq" },
    { key: "auto_wah_peak", label: "Peak" },
    { key: "auto_wah_level", label: "Level" },
    { key: "auto_wah_direct_mix", label: "Direct" },
    { key: "auto_wah_mode", label: "Mode" }
  ],
  "Comp": [
    { key: "comp_sustain", label: "Sustain" },
    { key: "comp_attack", label: "Attack" },
    { key: "comp_tone", label: "Tone" },
    { key: "comp_level", label: "Level" },
    { key: "comp_type", label: "Type" }
  ],
  "Flanger": [
    { key: "flanger_rate", label: "Rate" },
    { key: "flanger_depth", label: "Depth" },
    { key: "flanger_manual", label: "Manual" },
    { key: "flanger_resonance", label: "Reso" },
    { key: "flanger_low_cut", label: "Low Cut" },
    { key: "flanger_level", label: "Level" },
    { key: "flanger_direct_mix", label: "Direct" }
  ],
  "Guitar Sim": [
    { key: "guitar_sim_type", label: "Type" },
    { key: "guitar_sim_low", label: "Low" },
    { key: "guitar_sim_high", label: "High" },
    { key: "guitar_sim_level", label: "Level" }
  ],
  "Limiter": [
    { key: "limiter_threshold", label: "Thresh" },
    { key: "limiter_ratio", label: "Ratio" },
    { key: "limiter_attack", label: "Attack" },
    { key: "limiter_release", label: "Release" },
    { key: "limiter_level", label: "Level" },
    { key: "limiter_type", label: "Type" }
  ],
  "Octave": [
    { key: "octave_range", label: "Range" },
    { key: "octave_level", label: "Level" },
    { key: "octave_direct_mix", label: "Direct" }
  ],
  "Phaser": [
    { key: "phaser_rate", label: "Rate" },
    { key: "phaser_depth", label: "Depth" },
    { key: "phaser_manual", label: "Manual" },
    { key: "phaser_resonance", label: "Reso" },
    { key: "phaser_step_rate", label: "Step" },
    { key: "phaser_level", label: "Level" },
    { key: "phaser_direct_mix", label: "Direct" },
    { key: "phaser_type", label: "Type" }
  ],
  "Rotary": [
    { key: "rotary_rate_fast", label: "Rate" },
    { key: "rotary_depth", label: "Depth" },
    { key: "rotary_level", label: "Level" }
  ],
  "T Wah": [
    { key: "t_wah_sens", label: "Sens" },
    { key: "t_wah_frequency", label: "Freq" },
    { key: "t_wah_peak", label: "Peak" },
    { key: "t_wah_polarity", label: "Polarity" },
    { key: "t_wah_mode", label: "Mode" },
    { key: "t_wah_level", label: "Level" },
    { key: "t_wah_direct_mix", label: "Direct" }
  ],
  "Tremolo": [
    { key: "tremolo_rate", label: "Rate" },
    { key: "tremolo_depth", label: "Depth" },
    { key: "tremolo_waveshape", label: "Wave" },
    { key: "tremolo_level", label: "Level" }
  ],
  "Uni-V": [
    { key: "uni_v_rate", label: "Rate" },
    { key: "uni_v_depth", label: "Depth" },
    { key: "uni_v_level", label: "Level" }
  ],
  "Wave Synth": [
    { key: "wave_synth_wave", label: "Wave" },
    { key: "wave_synth_cutoff", label: "Cutoff" },
    { key: "wave_synth_resonance", label: "Reso" },
    { key: "wave_synth_sens", label: "Sens" },
    { key: "wave_synth_decay", label: "Decay" },
    { key: "wave_synth_depth", label: "Depth" },
    { key: "wave_synth_level", label: "Level" }
  ]
};

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

export const REVERB_PARAMS = [
  { key: "reverb_type", label: "Type" },
  { key: "reverb_time", label: "Time" },
  { key: "reverb_level", label: "Level" },
  { key: "reverb_direct_mix", label: "Direct" }
];

export const WAH_PARAMS = [
  { key: "wah_type", label: "Voicing" },
  { key: "pedal_type", label: "Mode" },
  { key: "wah_pedal_min", label: "Pedal Min" },
  { key: "wah_pedal_max", label: "Pedal Max" },
  { key: "wah_level", label: "Level" },
  { key: "wah_direct_mix", label: "Direct" }
];

export const GATE_PARAMS = [
  { key: "noise_suppressor_threshold", label: "Threshold" },
  { key: "noise_suppressor_release", label: "Release" }
];

export const delayParams = (prefix) => [
  { key: `${prefix}_type`, label: "Type" },
  { key: `${prefix}_time`, label: "Time", unit: "ms" },
  { key: `${prefix}_feedback`, label: "Feedback" },
  { key: `${prefix}_high_cut`, label: "High Cut" },
  { key: `${prefix}_level`, label: "Level" },
  { key: `${prefix}_direct_mix`, label: "Direct" },
];

/** Merge a display label with the amp's real range/kind. */
export function resolve(display) {
  const param = PARAM_BY_KEY[display.key];
  if (!param) throw new Error(`Unknown parameter ${display.key} - not in params.py`);
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

