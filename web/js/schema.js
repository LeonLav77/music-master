// The amp's parameters - names, ranges and enum options - fetched from the
// server at startup, so Python's tables in katana.py are the only copy.
//
// Top-level await: every module that imports this one waits until the
// schema has arrived, so the rest of the UI can use PARAMS as a plain
// constant. app.js loads Alpine only after that, for the same reason.

import { BASE } from "./transport.js";

const response = await fetch(`${BASE}/api/parameters`);
if (!response.ok) {
  throw new Error(`Could not load the parameter schema: ${response.status}`);
}

/** The server's shape, reshaped into what the UI uses. */
function fromServer(p) {
  const param = { key: p.name, kind: p.kind, group: p.group, readOnly: !p.writable };
  if (p.kind === "enum") {
    // Values are the amp's own numbers, not list positions - the numbering
    // has gaps (no boost 7, no effect 5/8/11/13/17).
    param.options = Object.entries(p.options)
      .map(([value, label]) => ({ value: Number(value), label }))
      .sort((a, b) => a.value - b.value);
  } else {
    param.min = p.min;
    param.max = p.max;
  }
  if (p.unit) param.unit = p.unit;
  return param;
}

export const PARAMS = (await response.json()).map(fromServer);

export const PARAM_BY_KEY = Object.fromEntries(PARAMS.map((p) => [p.key, p]));

/** Options for an enum parameter, or [] if it is not one. */
export function optionsFor(key) {
  return PARAM_BY_KEY[key]?.options ?? [];
}

/** The label the amp uses for a value, e.g. labelFor("fx1_type", 6). */
export function labelFor(key, value) {
  const found = optionsFor(key).find((o) => o.value === value);
  return found ? found.label : String(value);
}

export const AMP_MODEL_OPTIONS = optionsFor("amp_type");
export const FX_TYPE_OPTIONS = optionsFor("fx1_type");

// --- Fixed UI data ---------------------------------------------------------
// Interface decisions rather than amp facts, so they live here, not in Python.

// `pc` is the Program Change number that selects the channel (from the amp's
// manual). The names are placeholders until the amp reports its own.
export const CHANNELS = [
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

export const LED_COLORS = ["off", "green", "red", "yellow"];

export const FOOTSWITCHES = [
  { cc: 16, label: "BOOST", block: "boost_switch" },
  { cc: 17, label: "MOD", block: "fx1_switch" },
  { cc: 18, label: "FX", block: "fx2_switch" },
  { cc: 19, label: "DELAY", block: "delay_switch" },
  { cc: 20, label: "REVERB", block: "reverb_switch" },
  { cc: 21, label: "LOOP", block: null },
];
