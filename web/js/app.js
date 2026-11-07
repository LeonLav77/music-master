// Wires the store and components into Alpine, then starts it.
//
// Loaded as a module so it can import. Alpine is loaded at the bottom of
// this file, once everything is registered on alpine:init.

import { createKatanaStore } from "./store.js";
import { createPracticeStore } from "./practice.js";
import { createTunerStore, tunerDock } from "./tuner.js";
import { createRecorderStore } from "./recorder.js";
import { createWifiStore } from "./wifi.js";
import { knob, ampDial, treadle, eqPad, channelRail } from "./components.js";
import { transport } from "./transport.js";
import { CHANNELS, FOOTSWITCHES, labelFor, FX_TYPE_OPTIONS } from "./schema.js";
import {
  BLOCK_TITLES, AMP_PARAMS, BOOST_PARAMS, GATE_PARAMS, HARMONIST_TYPE, MASTER_KEY,
  contourParams, delayParams, effectParams, eqParams, reverbParams, wahParams, panel,
} from "./blocks.js";

// The Pi's own touch screen opens the page as /?kiosk (deploy/kiosk-browser).
// There a long press must not open a menu - see .kiosk in app.css too.
if (new URLSearchParams(location.search).has("kiosk")) {
  document.documentElement.classList.add("kiosk");
  document.addEventListener("contextmenu", (event) => event.preventDefault());
}

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
  Alpine.store("wifi", createWifiStore());
  Alpine.store("wifi").init();

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
    get wifi() { return Alpine.store("wifi"); },
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
        case "amp":
          return panel([...AMP_PARAMS, ...contourParams(amp.num("contour_select") + 1)]);
        case "boost":
          return panel(BOOST_PARAMS);
        case "mod":
        case "fx": {
          // Each slot has its own copy of every effect's knobs (fx1_... and
          // fx2_...), so editing slot 2 never touches slot 1.
          const slot = id === "mod" ? 1 : 2;
          const typeKey = `fx${slot}_type`;
          const type = amp.num(typeKey);
          const params = effectParams(slot, type);
          if (type === HARMONIST_TYPE) params.push(MASTER_KEY);
          return {
            fxSlot: { typeKey, options: FX_TYPE_OPTIONS, current: type, name: labelFor(typeKey, type) },
            ...panel(params, params.length ? null : `Type ${type} is accepted by the amp, but no effect uses it.`),
          };
        }
        case "delay": {
          const params = [
            ...delayParams("delay", amp.num("delay_type")),
            ...delayParams("delay2", amp.num("delay2_type")),
          ];
          const built = panel(params);
          built.toggles.unshift({ key: "delay2_switch", label: "Delay 2", kind: "toggle" });
          return built;
        }
        case "reverb":
          return panel(reverbParams(amp.num("reverb_type")));
        case "gate":
          return panel(GATE_PARAMS);
        case "wah":
          return panel(wahParams(amp.num("pedal_type")));
        case "eq":
          return panel(eqParams(amp.num("eq_type")));
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
