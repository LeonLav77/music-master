#!/usr/bin/env python3
"""Generate the interface's parameter schema from the amp library.

The server and the UI must agree about 154 parameters, their ranges and
their enum values. Maintaining that by hand in two languages guarantees
drift, so this writes the TypeScript from the Python tables.

    ./venv/bin/python scripts/generate_schema.py

Writes interface/src/lib/katana/generated.ts. Do not edit that file.
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
OUT = ROOT / "interface" / "src" / "lib" / "katana" / "generated.ts"

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

    lines = [
        "// GENERATED FILE - do not edit.",
        "// Written by scripts/generate_schema.py from the Python parameter",
        "// tables, so the UI and the amp cannot disagree about ranges or",
        "// enum numbering. Re-run that script after changing katana.py.",
        "",
        "export type ParamKind = \"range\" | \"toggle\" | \"enum\";",
        "",
        "export type EnumOption = { value: number; label: string };",
        "",
        "export type ParamDef = {",
        "  key: string;",
        "  kind: ParamKind;",
        "  group: string;",
        "  readOnly: boolean;",
        "  min?: number;",
        "  max?: number;",
        "  unit?: string;",
        "  /** Enum values are the amp's own numbers, which are sparse. */",
        "  options?: EnumOption[];",
        "};",
        "",
        f"export const PARAMS: ParamDef[] = {ts(params)};",
        "",
        "export const PARAM_BY_KEY: Record<string, ParamDef> =",
        "  Object.fromEntries(PARAMS.map((p) => [p.key, p]));",
        "",
        "/** Options for an enum parameter, or [] if it is not one. */",
        "export function optionsFor(key: string): EnumOption[] {",
        "  return PARAM_BY_KEY[key]?.options ?? [];",
        "}",
        "",
        "/** The label the amp uses for a value, e.g. labelFor(\"fx1_type\", 6). */",
        "export function labelFor(key: string, value: number): string {",
        "  const found = optionsFor(key).find((o) => o.value === value);",
        "  return found ? found.label : String(value);",
        "}",
        "",
        f"export const EQ_BAND_KEYS: string[] = {ts(EQ_BANDS_ORDER)};",
        "",
        "export type ChannelId =",
        "  " + " | ".join(f'"{name}"' for name in CHANNELS) + ";",
        "",
        "export const CHANNELS: { id: ChannelId; bank: string; pc: number }[] =",
        "  " + ts([
            {
                "id": name,
                "bank": "A" if name.startswith("a") else "B" if name.startswith("b") else "—",
                "pc": program,
            }
            for name, program in CHANNELS.items()
        ]) + ";",
        "",
        f"export const CONTROL_CHANGES: Record<string, number> = {ts(CONTROL_CHANGES)};",
        "",
        "/** Effects whose own knobs are mapped; others are selectable only. */",
        f"export const MAPPED_EFFECTS: string[] = {ts(sorted(MAPPED_EFFECTS))};",
        "",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))

    # schema.ts looks parameters up by name at runtime, so a typo there is
    # invisible to the type checker and only shows as a blank page. Check
    # every key it references actually exists.
    schema_ts = OUT.parent / "schema.ts"
    if schema_ts.exists():
        known = {entry["name"] for entry in schema}
        referenced = set(re.findall(r'\b[rte]\(\s*"([a-z0-9_]+)"', schema_ts.read_text()))
        missing = sorted(referenced - known)
        if missing:
            print(f"\n  WARNING: schema.ts references unknown parameters: {', '.join(missing)}")
            print("  Those lookups throw at render time. Fix the names in schema.ts.")
    enums = sum(1 for p in params if p["kind"] == "enum")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  {len(params)} parameters, {enums} enums")


if __name__ == "__main__":
    main()
