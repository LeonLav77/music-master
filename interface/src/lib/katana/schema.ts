// Katana MkII parameter schema.
//
// Ranges and enum *values* come from generated.ts, which is written from
// the Python tables by scripts/generate_schema.py - so the UI cannot
// disagree with the amp about what a number means. Labels, ordering and
// grouping live here, because those are interface decisions.

import {
  PARAM_BY_KEY,
  optionsFor,
  labelFor,
  type EnumOption,
  type ParamKind,
} from "./generated";

export {
  PARAMS,
  PARAM_BY_KEY,
  optionsFor,
  labelFor,
  MAPPED_EFFECTS,
  type EnumOption,
  type ParamKind,
} from "./generated";

export type ParamDef = {
  key: string;
  label: string;
  kind: ParamKind;
  min?: number;
  max?: number;
  unit?: string;
  /** Amp's own numbering - sparse, so never index into this. */
  options?: EnumOption[];
  readOnly?: boolean;
  /** Blocks that only answer when loaded in a slot -> can be genuinely unknown. */
  mayBeUnknown?: boolean;
};

/** Build a definition from the generated schema, adding a display label. */
function def(key: string, label: string, extra: Partial<ParamDef> = {}): ParamDef {
  const g = PARAM_BY_KEY[key];
  if (!g) throw new Error(`Unknown parameter ${key} - regenerate generated.ts`);
  const out: ParamDef = { key, label, kind: g.kind, readOnly: g.readOnly };
  if (g.min !== undefined) out.min = g.min;
  if (g.max !== undefined) out.max = g.max;
  if (g.unit !== undefined) out.unit = g.unit;
  if (g.options !== undefined) out.options = g.options;
  return { ...out, ...extra };
}

const r = def;
const t = def;
const e = (key: string, label: string, extra: Partial<ParamDef> = {}) =>
  def(key, label, extra);

/** Labels only - the values live in generated.ts. */
export const AMP_MODEL_OPTIONS = optionsFor("amp_type");
export const BOOST_TYPE_OPTIONS = optionsFor("boost_type");
export const DELAY_TYPE_OPTIONS = optionsFor("delay_type");
export const REVERB_TYPE_OPTIONS = optionsFor("reverb_type");
export const WAH_TYPE_OPTIONS = optionsFor("wah_type");
export const PEDAL_MODE_OPTIONS = optionsFor("pedal_type");
export const FX_TYPE_OPTIONS = optionsFor("fx1_type");


/** Indices reachable from the amp's own front panel. */
export const PANEL_AMP_MODELS = [0, 1, 2, 4, 7];
/** MkII-only, undocumented. */
export const UNDOCUMENTED_AMP_MODELS = [28, 29, 30, 31, 32];




/** Effects whose knobs are mapped. Anything else renders an "not mapped" notice. */
export const FX_PARAM_MAP: Record<string, ParamDef[]> = {
  "Auto Wah": [
    r("auto_wah_rate", "Rate"),
    r("auto_wah_depth", "Depth"),
    r("auto_wah_frequency", "Freq"),
    r("auto_wah_peak", "Peak"),
    r("auto_wah_level", "Level"),
    r("auto_wah_direct_mix", "Direct"),
    r("auto_wah_mode", "Mode"),
  ],
  Comp: [
    r("comp_sustain", "Sustain"),
    r("comp_attack", "Attack"),
    r("comp_tone", "Tone"),
    r("comp_level", "Level"),
    r("comp_type", "Type"),
  ],
  Flanger: [
    r("flanger_rate", "Rate"),
    r("flanger_depth", "Depth"),
    r("flanger_manual", "Manual"),
    r("flanger_resonance", "Reso"),
    r("flanger_low_cut", "Low Cut"),
    r("flanger_level", "Level"),
    r("flanger_direct_mix", "Direct"),
  ],
  "Guitar Sim": [
    r("guitar_sim_type", "Type"),
    r("guitar_sim_low", "Low"),
    r("guitar_sim_high", "High"),
    r("guitar_sim_level", "Level"),
  ],
  Limiter: [
    r("limiter_threshold", "Thresh"),
    r("limiter_ratio", "Ratio"),
    r("limiter_attack", "Attack"),
    r("limiter_release", "Release"),
    r("limiter_level", "Level"),
    r("limiter_type", "Type"),
  ],
  Octave: [
    r("octave_range", "Range"),
    r("octave_level", "Level"),
    r("octave_direct_mix", "Direct"),
  ],
  Phaser: [
    r("phaser_rate", "Rate"),
    r("phaser_depth", "Depth"),
    r("phaser_manual", "Manual"),
    r("phaser_resonance", "Reso"),
    r("phaser_step_rate", "Step"),
    r("phaser_level", "Level"),
    r("phaser_direct_mix", "Direct"),
    r("phaser_type", "Type"),
  ],
  Rotary: [r("rotary_rate_fast", "Rate"), r("rotary_depth", "Depth"), r("rotary_level", "Level")],
  "T Wah": [
    r("t_wah_sens", "Sens"),
    r("t_wah_frequency", "Freq"),
    r("t_wah_peak", "Peak"),
    r("t_wah_polarity", "Polarity"),
    r("t_wah_mode", "Mode"),
    r("t_wah_level", "Level"),
    r("t_wah_direct_mix", "Direct"),
  ],
  Tremolo: [
    r("tremolo_rate", "Rate"),
    r("tremolo_depth", "Depth"),
    r("tremolo_waveshape", "Wave"),
    r("tremolo_level", "Level"),
  ],
  "Uni-V": [r("uni_v_rate", "Rate"), r("uni_v_depth", "Depth"), r("uni_v_level", "Level")],
  "Wave Synth": [
    r("wave_synth_wave", "Wave"),
    r("wave_synth_cutoff", "Cutoff"),
    r("wave_synth_resonance", "Reso"),
    r("wave_synth_sens", "Sens"),
    r("wave_synth_decay", "Decay"),
    r("wave_synth_depth", "Depth"),
    r("wave_synth_level", "Level"),
  ],
};

export const AMP_PARAMS: ParamDef[] = [
  e("amp_type", "Amp"),
  r("gain", "Gain"),
  r("bass", "Bass"),
  r("middle", "Middle"),
  r("treble", "Treble"),
  r("presence", "Presence"),
  r("volume", "Volume"),
  t("bright", "Bright"),
  r("knob_volume", "Knob Vol", { readOnly: true }),
];

export const BOOST_PARAMS: ParamDef[] = [
  e("boost_type", "Pedal"),
  r("boost_drive", "Drive"),
  r("boost_bottom", "Bottom"),
  r("boost_tone", "Tone"),
  r("boost_level", "Level"),
  r("boost_direct_mix", "Direct"),
  r("boost_solo_level", "Solo Lvl"),
  t("boost_solo_switch", "Solo"),
];

export const delayParams = (p: "delay" | "delay2"): ParamDef[] => [
  e(`${p}_type`, "Type"),
  r(`${p}_time`, "Time", { unit: "ms" }),
  r(`${p}_feedback`, "Feedback"),
  r(`${p}_high_cut`, "High Cut"),
  r(`${p}_level`, "Level"),
  r(`${p}_direct_mix`, "Direct"),
];

export const REVERB_PARAMS: ParamDef[] = [
  e("reverb_type", "Type"),
  r("reverb_time", "Time"),
  r("reverb_level", "Level"),
  r("reverb_direct_mix", "Direct"),
];

export const WAH_PARAMS: ParamDef[] = [
  e("wah_type", "Voicing"),
  e("pedal_type", "Mode"),
  r("wah_pedal_min", "Pedal Min"),
  r("wah_pedal_max", "Pedal Max"),
  r("wah_level", "Level"),
  r("wah_direct_mix", "Direct"),
];

export const GATE_PARAMS: ParamDef[] = [
  r("noise_suppressor_threshold", "Threshold"),
  r("noise_suppressor_release", "Release"),
];

export const EQ_BANDS = [
  { key: "eq_band_31hz", label: "31" },
  { key: "eq_band_62hz", label: "62" },
  { key: "eq_band_125hz", label: "125" },
  { key: "eq_band_250hz", label: "250" },
  { key: "eq_band_500hz", label: "500" },
  { key: "eq_band_1khz", label: "1k" },
  { key: "eq_band_2khz", label: "2k" },
  { key: "eq_band_4khz", label: "4k" },
  { key: "eq_band_8khz", label: "8k" },
  { key: "eq_band_16khz", label: "16k" },
];

export const LED_COLORS = ["off", "green", "red", "yellow"] as const;
export type LedColor = (typeof LED_COLORS)[number];

export type ChannelId = "a1" | "a2" | "a3" | "a4" | "panel" | "b1" | "b2" | "b3" | "b4";

export const CHANNELS: { id: ChannelId; bank: string; pc: number; name: string }[] = [
  { id: "a1", bank: "A", pc: 1, name: "Iron Bell" },
  { id: "a2", bank: "A", pc: 2, name: "Sabbath Fuzz" },
  { id: "a3", bank: "A", pc: 3, name: "Black Winter" },
  { id: "a4", bank: "A", pc: 4, name: "Downhill Lead" },
  { id: "panel", bank: "—", pc: 5, name: "PANEL" },
  { id: "b1", bank: "B", pc: 6, name: "Scoop Rhythm" },
  { id: "b2", bank: "B", pc: 7, name: "Glass Clean" },
  { id: "b3", bank: "B", pc: 8, name: "Wide Ambient" },
  { id: "b4", bank: "B", pc: 9, name: "Sinergy Shred" },
];

export const FOOTSWITCHES = [
  { cc: 16, label: "BOOST", block: "boost_switch" },
  { cc: 17, label: "MOD", block: "fx1_switch" },
  { cc: 18, label: "FX", block: "fx2_switch" },
  { cc: 19, label: "DELAY", block: "delay_switch" },
  { cc: 20, label: "REVERB", block: "reverb_switch" },
  { cc: 21, label: "LOOP", block: null },
] as const;
