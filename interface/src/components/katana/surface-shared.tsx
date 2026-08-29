import { labelFor } from "@/lib/katana/schema";
import type { BlockId } from "./BlockEditor";

export const AMP_KNOBS = [
  { key: "gain", label: "Gain", accent: "ember" as const },
  { key: "bass", label: "Bass", accent: "steel" as const },
  { key: "middle", label: "Middle", accent: "steel" as const },
  { key: "treble", label: "Treble", accent: "steel" as const },
  { key: "presence", label: "Presence", accent: "steel" as const },
  { key: "volume", label: "Volume", accent: "steel" as const },
];

export type Block = {
  id: BlockId;
  label: string;
  sw: string;
  sub: string;
  led?: string;
};

type K = { num: (k: string) => number };

export function buildBlocks(k: K): Block[] {
  return [
    { id: "boost", label: "Boost", sw: "boost_switch", sub: labelFor("boost_type", k.num("boost_type")), led: "led_boost" },
    { id: "mod", label: "Mod", sw: "fx1_switch", sub: labelFor("fx1_type", k.num("fx1_type")), led: "led_mod" },
    { id: "fx", label: "FX", sw: "fx2_switch", sub: labelFor("fx2_type", k.num("fx2_type")), led: "led_fx" },
    {
      id: "delay",
      label: "Delay",
      sw: "delay_switch",
      sub: `${labelFor("delay_type", k.num("delay_type"))} · ${k.num("delay_time")}ms`,
      led: "led_delay",
    },
    { id: "reverb", label: "Reverb", sw: "reverb_switch", sub: labelFor("reverb_type", k.num("reverb_type")), led: "led_reverb" },
    { id: "gate", label: "Gate", sw: "noise_suppressor_switch", sub: `thr ${k.num("noise_suppressor_threshold")}` },
  ];
}
