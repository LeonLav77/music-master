// Wires the store and components into Alpine, then starts it.
//
// Loaded as a module so it can import; Alpine itself is loaded deferred from
// the CDN and picks up everything registered on alpine:init.

import { createKatanaStore } from "./store.js";
import { knob, ampDial, treadle, eqPad, channelRail, wahRock, scrubber, tapTempo } from "./components.js";
import { createDeckStore } from "./deck.js";
import { transport } from "./transport.js";
import {
  CHANNELS, FOOTSWITCHES, EQ_BANDS, labelFor,
  BOOST_TYPE_OPTIONS, DELAY_TYPE_OPTIONS, REVERB_TYPE_OPTIONS,
  WAH_TYPE_OPTIONS, PEDAL_TYPE_OPTIONS, FX_TYPE_OPTIONS,
} from "./schema.js";
import {
  BLOCK_TITLES, FX_PARAM_MAP, BOOST_PARAMS, REVERB_PARAMS, WAH_PARAMS,
  GATE_PARAMS, delayParams, knobParams, enumParams, toggleParams,
} from "./blocks.js";

/** The six pedal tiles on the board. */
function buildBlocks(k) {
  return [
    { id: "boost",  label: "Boost",  sw: "boost_switch",  led: "led_boost",  sub: labelFor("boost_type", k.num("boost_type")) },
    { id: "mod",    label: "Mod",    sw: "fx1_switch",    led: "led_mod",    sub: labelFor("fx1_type", k.num("fx1_type")) },
    { id: "fx",     label: "FX",     sw: "fx2_switch",    led: "led_fx",     sub: labelFor("fx2_type", k.num("fx2_type")) },
    { id: "delay",  label: "Delay",  sw: "delay_switch",  led: "led_delay",  sub: `${labelFor("delay_type", k.num("delay_type"))} · ${k.num("delay_time")}ms` },
    { id: "reverb", label: "Reverb", sw: "reverb_switch", led: "led_reverb", sub: labelFor("reverb_type", k.num("reverb_type")) },
    { id: "gate",   label: "Gate",   sw: "noise_suppressor_switch", led: null, sub: `thr ${k.num("noise_suppressor_threshold")}` },
  ];
}

const TILE_COLOR = {
  Boost: "coral", Mod: "cyan", FX: "lime",
  Delay: "violet", Reverb: "cyan", Gate: "coral",
};

document.addEventListener("alpine:init", () => {
  Alpine.store("katana", createKatanaStore());
  Alpine.store("katana").init();

  // The deck is its own store, matching the server split: it never touches
  // an amp parameter, and it keeps working with the amp switched off.
  Alpine.store("deck", createDeckStore());
  Alpine.store("deck").init();

  Alpine.data("knob", knob);
  Alpine.data("ampDial", ampDial);
  Alpine.data("treadle", treadle);
  Alpine.data("eqPad", eqPad);
  Alpine.data("channelRail", channelRail);
  Alpine.data("wahRock", wahRock);
  Alpine.data("scrubber", scrubber);
  Alpine.data("tapTempo", tapTempo);

  /** The whole desk: layout-level state only. */
  Alpine.data("desk", () => ({
    openBlock: null,
    // Which half of the rig is on screen. The deck is a separate page
    // rather than another panel: it is a different job, and the amp
    // surface is already full at the sizes this runs on.
    page: "amp",
    channels: CHANNELS,
    footswitches: FOOTSWITCHES,
    eqBands: EQ_BANDS,
    ampKnobs: [
      { key: "gain", label: "Gain", accent: "ember" },
      { key: "bass", label: "Bass", accent: "steel" },
      { key: "middle", label: "Middle", accent: "steel" },
      { key: "treble", label: "Treble", accent: "steel" },
      { key: "presence", label: "Presence", accent: "steel" },
      { key: "volume", label: "Volume", accent: "steel" },
    ],
    titles: BLOCK_TITLES,

    get k() { return Alpine.store("katana"); },
    get d() { return Alpine.store("deck"); },
    get blocks() { return buildBlocks(this.k); },
    get glowing() { return this.k.bool("bright") || this.k.dirty; },
    tileColor(label) { return TILE_COLOR[label] ?? "coral"; },

    resync() { this.k.resync(); },
    pressFootswitch(fs) {
      // One command, not two: toggling the parameter already switches the
      // block on the amp. Sending the CC as well would fight it, and CC 127
      // always means "on" - pressing an active footswitch would desync.
      if (fs.block) this.k.toggle(fs.block);
      else transport.sendCC(fs.cc, 127);
    },
    sweepWah() {
      transport.sweepWah(this.k.num("wah_pedal_min"), this.k.num("wah_pedal_max"), 900);
    },

    // ---- block editor ----
    get editor() {
      const id = this.openBlock;
      if (!id) return null;
      const k = this.k;
      switch (id) {
        case "boost":
          return { enums: enumParams(BOOST_PARAMS), knobs: knobParams(BOOST_PARAMS), toggles: toggleParams(BOOST_PARAMS), note: null };
        case "mod":
        case "fx": {
          const slot = id === "mod" ? 1 : 2;
          const typeKey = `fx${slot}_type`;
          const name = labelFor(typeKey, k.num(typeKey));
          const params = FX_PARAM_MAP[name];
          return {
            fxSlot: { typeKey, options: FX_TYPE_OPTIONS, current: k.num(typeKey), name },
            enums: [], toggles: [],
            knobs: params ? knobParams(params) : [],
            note: params ? null : `${name} is selectable but its parameters are not mapped — values read back as unknown, not zero.`,
          };
        }
        case "delay": {
          const a = delayParams("delay"), b = delayParams("delay2");
          return {
            enums: [...enumParams(a), ...enumParams(b)],
            knobs: [...knobParams(a), ...knobParams(b)],
            toggles: [{ key: "delay2_switch", label: "Delay 2", kind: "toggle" }],
            note: null,
          };
        }
        case "reverb":
          return { enums: enumParams(REVERB_PARAMS), knobs: knobParams(REVERB_PARAMS), toggles: [], note: null };
        case "gate":
          return { enums: [], knobs: knobParams(GATE_PARAMS), toggles: [], note: null };
        case "wah":
          return { enums: enumParams(WAH_PARAMS), knobs: knobParams(WAH_PARAMS), toggles: [], note: null };
        case "eq":
          return { enums: [], knobs: knobParams([{ key: "eq_level", label: "EQ Level" }]), toggles: [], note: null, showEq: true };
        default:
          return null;
      }
    },
  }));
});
