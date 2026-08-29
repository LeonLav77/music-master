#!/usr/bin/env bash
# Play a backing track out the machine's analog jack, for feeding the
# Katana's AUX IN over a 3.5mm cable.
#
# Why AUX rather than USB: the Katana's USB input lands at the *input* stage
# (re-amp mode) - the track picks up the amp model and gain, and the guitar
# jack goes dead. AUX IN mixes in after the modelling instead, so the track
# stays clean and the guitar is untouched. Different jack, different path.
#
# Usage: aux-play.sh <track> [volume]     volume: 0.0-1.0, default 1.0
#
# The analog jack is low-power and the amp's AUX IN wants line level, so this
# runs at unity gain. Balance against the guitar with the amp's master +
# channel volume, not by pushing this above 1.0 (it clips).
#
# Sink selection: set AUX_SINK to a node.name to pin one explicitly. Otherwise
# the first analog ALSA sink is used - correct on both a laptop (headphone
# jack) and a Pi (3.5mm out), whose node names differ. We never fall back to
# the *default* sink: that follows whatever connected last (Bluetooth
# headphones, HDMI) and would silently play anywhere but the amp.

set -euo pipefail

TRACK="${1:?usage: aux-play.sh <track> [volume]}"
VOL="${2:-1.0}"

[ -r "$TRACK" ] || { echo "no such file: $TRACK" >&2; exit 1; }

sinks() { pw-cli ls Node 2>/dev/null | grep -oE '(alsa_output|bluez_output)[^"]*'; }

if [ -n "${AUX_SINK:-}" ]; then
  SINK="$AUX_SINK"
  sinks | grep -qx "$SINK" || { echo "AUX_SINK '$SINK' not present" >&2; sinks >&2; exit 1; }
else
  # Prefer an analog ALSA sink; exclude HDMI and the Katana's own USB audio
  # (sending audio there triggers re-amp mode - the whole thing we avoid).
  SINK="$(sinks | grep '^alsa_output' | grep -v -e hdmi -e KATANA | head -1 || true)"
  [ -n "$SINK" ] || { echo "no analog sink found; set AUX_SINK explicitly" >&2; sinks >&2; exit 1; }
fi

echo "-> $SINK  (vol $VOL)" >&2
exec pw-play --target "$SINK" --volume "$VOL" "$TRACK"
