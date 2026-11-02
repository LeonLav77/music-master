// The hidden /wifi page: the saved Wi-Fi networks, forgetting them and
// adding new ones. Nothing links here - type the address.
//
// Plain HTTP only: the list is read when the page opens and again after
// every change, which is all a settings page needs.

import { transport } from "./transport.js";

document.addEventListener("alpine:init", () => {
  Alpine.data("wifiPage", () => ({
    loading: true,
    state: null,          // { available, mode, network, hotspot }
    saved: [],            // [{ uuid, ssid, active }]
    nearby: [],           // names in range, strongest first
    error: null,
    ssid: "",
    password: "",
    showPassword: false,
    saving: false,
    pendingForget: null,  // the network waiting for "are you sure?"

    get status() {
      if (!this.state) return "";
      switch (this.state.mode) {
        case "online": return `Connected to ${this.state.network}`;
        case "hotspot": return `No Wi-Fi - this is the ${this.state.hotspot.ssid} hotspot`;
        case "connecting": return "Trying the saved networks…";
        default: return "Not connected";
      }
    },
    get passwordProblem() {
      const length = this.password.length;
      return length > 0 && (length < 8 || length > 63) ? "A Wi-Fi password is 8-63 characters" : null;
    },

    async load() {
      try {
        const { saved, nearby, ...state } = await transport.wifi();
        Object.assign(this, { state, saved, nearby, error: null });
      } catch (error) {
        this.error = error.message;
      }
      this.loading = false;
    },

    async add() {
      if (!this.ssid.trim() || this.passwordProblem) return;
      this.saving = true;
      try {
        await transport.addWifi(this.ssid.trim(), this.password);
        this.ssid = "";
        this.password = "";
        await this.load();
      } catch (error) {
        this.error = error.message;
      }
      this.saving = false;
    },

    async confirmForget() {
      const network = this.pendingForget;
      this.pendingForget = null;
      try {
        await transport.forgetWifi(network.uuid);
        await this.load();
      } catch (error) {
        this.error = error.message;
      }
    },

    init() { this.load(); },
  }));
});
