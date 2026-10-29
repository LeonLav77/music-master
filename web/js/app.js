// Wires the store and components into Alpine, then starts it.
//
// Loaded as a module so it can import. Alpine is loaded at the bottom of
// this file, once everything is registered on alpine:init.

import { createKatanaStore } from "./store.js";
import { createPracticeStore } from "./practice.js";
import { createTunerStore, tunerDock } from "./tuner.js";
import { createRecorderStore } from "./recorder.js";
import { knob, ampDial, treadle, eqPad, channelRail } from "./components.js";
import { transport } from "./transport.js";
import { CHANNELS, FOOTSWITCHES, labelFor, FX_TYPE_OPTIONS } from "./schema.js";
import {
  BLOCK_TITLES, FX_PARAM_MAP, BOOST_PARAMS, REVERB_PARAMS, WAH_PARAMS,
  GATE_PARAMS, delayParams, knobParams, enumParams, toggleParams,
} from "./blocks.js";

/** The six pedal tiles on the board. */
function buildBlocks(amp) {
  return [
    { id: "boost",  label: "Boost",  sw: "boost_switch",  led: "led_boost",  sub: labelFor("boost_type", amp.num("boost_type")) },
    { id: "mod",    label: "Mod",    sw: "fx1_switch",    led: "led_mod",    sub: labelFor("fx1_type", amp.num("fx1_type")) },
    { id: "fx",     label: "FX",     sw: "fx2_switch",    led: "led_fx",     sub: labelFor("fx2_type", amp.num("fx2_type")) },
    { id: "delay",  label: "Delay",  sw: "delay_switch",  led: "led_delay",  sub: `${labelFor("delay_type", amp.num("delay_type"))} · ${amp.num("delay_time")}ms` },
    { id: "reverb", label: "Reverb", sw: "reverb_switch", led: "led_reverb", sub: labelFor("reverb_type", amp.num("reverb_type")) },
    { id: "gate",   label: "Gate",   sw: "noise_suppressor_switch", led: null, sub: `thr ${amp.num("noise_suppressor_threshold")}` },
  ];
}

const TILE_COLOR = {
  Boost: "coral", Mod: "cyan", FX: "lime",
  Delay: "violet", Reverb: "cyan", Gate: "coral",
};

document.addEventListener("alpine:init", () => {
  Alpine.store("katana", createKatanaStore());
  Alpine.store("katana").init();
  Alpine.store("practice", createPracticeStore());
  Alpine.store("practice").init();
  Alpine.store("tuner", createTunerStore());
  Alpine.store("tuner").init();
  Alpine.store("recorder", createRecorderStore());
  Alpine.store("recorder").init();

  Alpine.data("knob", knob);
  Alpine.data("ampDial", ampDial);
  Alpine.data("treadle", treadle);
  Alpine.data("eqPad", eqPad);
  Alpine.data("channelRail", channelRail);
  Alpine.data("tunerDock", tunerDock);

  /** The whole desk: layout-level state only. */
  Alpine.data("desk", () => ({
    // "amp" or "practice". In the URL (#practice), so it can be bookmarked,
    // and remembered, so a reload stays on the same tab.
    tab: (() => {
      if (location.hash === "#practice" || location.hash === "#amp") return location.hash.slice(1);
      try { return localStorage.getItem("katana.tab") === "practice" ? "practice" : "amp"; } catch { return "amp"; }
    })(),
    openBlock: null,
    channels: CHANNELS,
    footswitches: FOOTSWITCHES,
    ampKnobs: [
      { key: "gain", label: "Gain", accent: "ember" },
      { key: "bass", label: "Bass", accent: "steel" },
      { key: "middle", label: "Middle", accent: "steel" },
      { key: "treble", label: "Treble", accent: "steel" },
      { key: "presence", label: "Presence", accent: "steel" },
      { key: "volume", label: "Volume", accent: "steel" },
    ],
    titles: BLOCK_TITLES,

    get amp() { return Alpine.store("katana"); },
    get practice() { return Alpine.store("practice"); },
    showTab(name) {
      this.tab = name;
      history.replaceState(null, "", `#${name}`);
      try { localStorage.setItem("katana.tab", name); } catch {}
    },
    get blocks() { return buildBlocks(this.amp); },
    get glowing() { return this.amp.bool("bright") || this.amp.dirty; },
    tileColor(label) { return TILE_COLOR[label] ?? "coral"; },

    resync() { this.amp.resync(); },
    pressFootswitch(fs) {
      // One command, not two: toggling the parameter already switches the
      // block on the amp. Sending the CC as well would fight it, and CC 127
      // always means "on" - pressing an active footswitch would desync.
      if (fs.block) this.amp.toggle(fs.block);
      else transport.sendCC(fs.cc, 127);
    },

    // ---- block editor ----
    get editor() {
      const id = this.openBlock;
      if (!id) return null;
      const amp = this.amp;
      switch (id) {
        case "boost":
          return { enums: enumParams(BOOST_PARAMS), knobs: knobParams(BOOST_PARAMS), toggles: toggleParams(BOOST_PARAMS), note: null };
        case "mod":
        case "fx": {
          const slot = id === "mod" ? 1 : 2;
          const typeKey = `fx${slot}_type`;
          const name = labelFor(typeKey, amp.num(typeKey));
          const params = FX_PARAM_MAP[name];
          return {
            fxSlot: { typeKey, options: FX_TYPE_OPTIONS, current: amp.num(typeKey), name },
            enums: [], toggles: [],
            knobs: params ? knobParams(params) : [],
            note: params ? null : `${name} is selectable but its parameters are not mapped — values read back as unknown, not zero.`,
          };
        }
        case "delay": {
          const delay1 = delayParams("delay"), delay2 = delayParams("delay2");
          return {
            enums: [...enumParams(delay1), ...enumParams(delay2)],
            knobs: [...knobParams(delay1), ...knobParams(delay2)],
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
          return { enums: [], knobs: knobParams([{ key: "eq_level", label: "EQ Level" }]), toggles: [], note: null };
        default:
          return null;
      }
    },
  }));
});

// Alpine is loaded here, not from index.html. This module only runs once
// schema.js has fetched the parameters, and Alpine fires alpine:init the
// moment it loads - loaded any earlier, it would start before the listener
// above existed and the page would come up empty.
const alpine = document.createElement("script");
alpine.src = "vendor/alpine.min.js";
document.head.append(alpine);
