#!/usr/bin/env python3
"""Generate the web surface's parameter schema from the amp library.

The server and the UI must agree about 154 parameters, their ranges and
their enum values. Maintaining that by hand in two languages guarantees
drift, so this writes the JavaScript from the Python tables.

    ./venv/bin/python scripts/generate_schema.py

Writes web/js/schema.js. Do not edit that file.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from katana_amp.katana import (
    CHANNELS,
    CONTROL_CHANGES,
    EQ_BANDS_ORDER,
    describe_parameters,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "js" / "schema.js"

# Display-side constants. These are interface decisions, not amp facts, so
# they live here rather than in katana.py - but they ship in the same file
# so the surface has one place to import from.

EQ_BAND_LABELS = ["31", "62", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]

FOOTSWITCHES = [
    (16, "BOOST", "boost_switch"),
    (17, "MOD", "fx1_switch"),
    (18, "FX", "fx2_switch"),
    (19, "DELAY", "delay_switch"),
    (20, "REVERB", "reverb_switch"),
    (21, "LOOP", None),
]

# Fallback names, shown until the amp reports its own patch names.
CHANNEL_NAMES = {
    "a1": "Iron Bell",
    "a2": "Sabbath Fuzz",
    "a3": "Black Winter",
    "a4": "Downhill Lead",
    "panel": "PANEL",
    "b1": "Scoop Rhythm",
    "b2": "Glass Clean",
    "b3": "Wide Ambient",
    "b4": "Sinergy Shred",
}

# Effects whose own parameters this project has mapped. Anything else is
# selectable but has no editable knobs yet.
MAPPED_EFFECTS = {
    "t_wah", "auto_wah", "comp", "limiter", "guitar_sim", "wave_synth",
    "octave", "phaser", "flanger", "tremolo", "vibrato", "uni_v",
    "rotary", "slicer", "ring_mod", "humanizer",
}


def ts(value):
    return json.dumps(value, ensure_ascii=False)


def main():
    schema = describe_parameters()

    params = []
    for entry in schema:
        item = {
            "key": entry["name"],
            "kind": entry["kind"],
            "group": entry["group"],
            "readOnly": not entry["writable"],
        }
        if entry["kind"] == "enum":
            # Values are NOT array indices - the amp's numbering has gaps
            # (no boost 7, no effect 5/8/11/13/17). Carry the real number.
            item["options"] = [
                {"value": int(value), "label": label}
                for value, label in sorted(
                    entry["options"].items(), key=lambda kv: int(kv[0])
                )
            ]
        else:
            item["min"] = entry["min"]
            item["max"] = entry["max"]
        if entry.get("unit"):
            item["unit"] = entry["unit"]
        params.append(item)

    channels = [
        {
            "id": name,
            "bank": "A" if name.startswith("a") else "B" if name.startswith("b") else "\u2014",
            "pc": program,
            "name": CHANNEL_NAMES.get(name, name.upper()),
        }
        for name, program in CHANNELS.items()
    ]

    lines = [
        "// GENERATED FILE - do not edit.",
        "// Written by scripts/generate_schema.py from the Python parameter",
        "// tables, so the UI and the amp cannot disagree about ranges or",
        "// enum numbering. Re-run that script after changing katana.py.",
        "//",
        "// Plain JS, no build step.",
        "",
        f"export const PARAMS = {ts(params)};",
        "",
        f"export const EQ_BAND_KEYS = {ts(EQ_BANDS_ORDER)};",
        "",
        f"export const CONTROL_CHANGES = {ts(CONTROL_CHANGES)};",
        "",
        "/** Effects whose own knobs are mapped; others are selectable only. */",
        f"export const MAPPED_EFFECTS = {ts(sorted(MAPPED_EFFECTS))};",
        "",
        f"export const CHANNELS = {ts(channels)};",
        "",
        "export const PARAM_BY_KEY = Object.fromEntries(PARAMS.map((p) => [p.key, p]));",
        "",
        "/** Options for an enum parameter, or [] if it is not one. */",
        "export function optionsFor(key) {",
        "  return PARAM_BY_KEY[key]?.options ?? [];",
        "}",
        "",
        "/** The label the amp uses for a value, e.g. labelFor(\"fx1_type\", 6). */",
        "export function labelFor(key, value) {",
        "  const found = optionsFor(key).find((o) => o.value === value);",
        "  return found ? found.label : String(value);",
        "}",
        "",
        "export const EQ_BANDS = [",
    ] + [
        f'  {{ key: "{key}", label: "{label}" }},'
        for key, label in zip(EQ_BANDS_ORDER, EQ_BAND_LABELS)
    ] + [
        "];",
        "",
        "export const LED_COLORS = [\"off\", \"green\", \"red\", \"yellow\"];",
        "",
        "export const FOOTSWITCHES = [",
    ] + [
        f'  {{ cc: {cc}, label: "{label}", block: {ts(block) if block else "null"} }},'
        for cc, label, block in FOOTSWITCHES
    ] + [
        "];",
        "",
        "export const AMP_MODEL_OPTIONS = optionsFor(\"amp_type\");",
        "export const BOOST_TYPE_OPTIONS = optionsFor(\"boost_type\");",
        "export const DELAY_TYPE_OPTIONS = optionsFor(\"delay_type\");",
        "export const REVERB_TYPE_OPTIONS = optionsFor(\"reverb_type\");",
        "export const WAH_TYPE_OPTIONS = optionsFor(\"wah_type\");",
        "export const FX_TYPE_OPTIONS = optionsFor(\"fx1_type\");",
        "export const PEDAL_TYPE_OPTIONS = optionsFor(\"pedal_type\");",
        "",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))

    enums = sum(1 for p in params if p["kind"] == "enum")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  {len(params)} parameters, {enums} enums")


if __name__ == "__main__":
    main()
