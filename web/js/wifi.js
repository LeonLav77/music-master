// The Wi-Fi store: whether the Pi is on a network or is its own hotspot.
//
// The server watches wlan0 (server/wifi.py) and sends a "wifi" message
// whenever that changes. The surface only needs it for one button: while
// the Pi is the hotspot, pressing it tries the saved networks again.

import { transport } from "./transport.js";

export function createWifiStore() {
  return {
    available: false,
    mode: "offline",      // "online", "offline", "hotspot" or "connecting"
    network: null,        // the network's name while online
    hotspot: null,        // { ssid, address }
    error: null,

    // ---- reads ----
    get connecting() { return this.mode === "connecting"; },
    get showButton() { return this.available && (this.mode === "hotspot" || this.connecting); },
    get title() {
      if (this.connecting) return "Trying the saved Wi-Fi networks…";
      return `No Wi-Fi: this is the ${this.hotspot?.ssid} hotspot, at http://${this.hotspot?.address}:8000. Tap to try the saved networks again.`;
    },

    // ---- actions ----
    async connect() {
      this.error = null;
      try {
        await transport.connectWifi();
      } catch (error) {
        this.error = error.message;
        console.error("[wifi] connect failed", error);
      }
    },

    init() {
      transport.onMessage((message) => {
        if (message.type !== "wifi") return;
        Object.assign(this, {
          available: message.available,
          mode: message.mode,
          network: message.network ?? null,
          hotspot: message.hotspot ?? null,
        });
      });
    },
  };
}
