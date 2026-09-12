#!/usr/bin/env bash
# Install the Katana control surface on a Raspberry Pi.
#
#     sudo ./deploy/install.sh
#
# Run this at home, on wifi. Everything it needs comes off the internet, and
# the whole point of the build is that the Pi works at a venue where there is
# none - so anything missing here cannot be fixed there.
#
# Safe to re-run: it updates an existing install in place.

set -euo pipefail

APP_USER=katana
APP_DIR=/opt/katana
STATE_DIR=/var/lib/katana
SRC="$(cd "$(dirname "$0")/.." && pwd)"

[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

# --- packages --------------------------------------------------------------
# python3-dev, build-essential and libasound2-dev are for python-rtmidi,
# which has no aarch64 wheel on PyPI and compiles from source.
#
# pipewire, ffmpeg: the aux deck plays backing tracks out the analog jack.
# ffmpeg also supplies ffprobe, which the deck uses to read durations.
#
# The X packages are the kiosk. Installed even on a headless Pi, on purpose:
# you asked for the screen to work the moment it is plugged in, and there is
# no internet at a venue to install them then. They cost disk, not RAM - with
# no display attached nothing here ever runs.
say "Installing packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  python3 python3-venv python3-dev build-essential libasound2-dev \
  pipewire pipewire-audio-client-libraries wireplumber pipewire-bin \
  ffmpeg curl ca-certificates rsync git \
  iw rfkill network-manager \
  xserver-xorg xinit x11-xserver-utils xinput unclutter

# Chromium separately, and last: it is named chromium-browser on Pi OS and
# chromium elsewhere. Bundled with the others, whichever name is wrong would
# fail the whole transaction and skip every package above it.
if ! apt-get install -y --no-install-recommends chromium-browser; then
  apt-get install -y --no-install-recommends chromium
fi

# --- user ------------------------------------------------------------------
# A service account rather than pi: audio for the ALSA MIDI port, plugdev for
# the raw USB device, video/render/input for the kiosk's X server.
say "Creating $APP_USER"
if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$STATE_DIR" \
          --shell /usr/sbin/nologin "$APP_USER"
fi
for group in audio plugdev video render input tty; do
  getent group "$group" >/dev/null && usermod -aG "$group" "$APP_USER"
done

install -d -o "$APP_USER" -g "$APP_USER" "$STATE_DIR" "$STATE_DIR/chromium"

# PipeWire is a user service. A system account never logs in, so without
# lingering it gets no user session, no runtime directory and no audio -
# the aux deck would find no sound card at all.
loginctl enable-linger "$APP_USER" 2>/dev/null || true

# Start it now so the first run has audio without waiting for a reboot.
uid=$(id -u "$APP_USER")
sudo -u "$APP_USER" XDG_RUNTIME_DIR="/run/user/$uid" \
  systemctl --user enable --now pipewire wireplumber 2>/dev/null || true

# The headphone jack comes up at 40%, which into an amp's AUX input is
# quiet enough to read as "no sound at all". Nudge it up once, on a fresh
# install only - clobbering a level the user has since set would be worse
# than leaving it low.
if [ ! -e "$STATE_DIR/.audio-set" ]; then
  sleep 2
  jack=$(sudo -u "$APP_USER" XDG_RUNTIME_DIR="/run/user/$uid" wpctl status 2>/dev/null |
         sed -n '/Sinks:/,/Sources:/p' | grep -i "built-in" |
         grep -oE '[0-9]+\.' | tr -d '.' | head -1)
  if [ -n "$jack" ]; then
    sudo -u "$APP_USER" XDG_RUNTIME_DIR="/run/user/$uid" wpctl set-volume "$jack" 0.85 2>/dev/null || true
    sudo -u "$APP_USER" XDG_RUNTIME_DIR="/run/user/$uid" wpctl set-mute "$jack" 0 2>/dev/null || true
  fi
  touch "$STATE_DIR/.audio-set"
  chown "$APP_USER:$APP_USER" "$STATE_DIR/.audio-set"
fi

# --- code ------------------------------------------------------------------
say "Installing to $APP_DIR"
install -d -o "$APP_USER" -g "$APP_USER" "$APP_DIR"

# --delete so a rename upstream does not leave the old file behind to be
# imported by accident. tracks/ and patches/ are the user's, never touched.
rsync -a --delete \
  --exclude venv/ --exclude .git/ --exclude __pycache__/ \
  --exclude tracks/ --exclude patches/ --exclude '*.wav' \
  "$SRC"/ "$APP_DIR"/

install -d -o "$APP_USER" -g "$APP_USER" "$APP_DIR/tracks" "$APP_DIR/patches"
# Patches ship with the app; tracks are added later over the web UI.
[ -d "$SRC/patches" ] && cp -n "$SRC"/patches/*.tsl "$APP_DIR/patches/" 2>/dev/null || true

chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod +x "$APP_DIR"/deploy/{display-changed,kiosk-session,wait-for-server} "$APP_DIR"/run

# --- python ----------------------------------------------------------------
# python-rtmidi compiles here. On a Pi 4 it is a couple of minutes; on a
# Zero 2 W it is slower and can run out of memory on 512 MB - if it dies,
# add swap and re-run rather than assuming the package is broken.
say "Building the virtualenv (rtmidi compiles - this takes a few minutes)"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# --- services --------------------------------------------------------------
say "Installing services"
# The service needs the katana user's runtime directory to reach PipeWire,
# and that path contains their uid - which is assigned at creation and is
# not the same on every machine.
uid=$(id -u "$APP_USER")
sed "s|__UID__|$uid|g" "$SRC/deploy/systemd/katana.service" \
  > /etc/systemd/system/katana.service
chmod 644 /etc/systemd/system/katana.service
install -m 644 "$SRC/deploy/systemd/katana-kiosk.service" /etc/systemd/system/
install -m 644 "$SRC/deploy/systemd/katana-net.service"   /etc/systemd/system/
install -m 644 "$SRC/deploy/systemd/katana-net.timer"     /etc/systemd/system/
install -m 644 "$SRC/deploy/udev/99-katana-display.rules" /etc/udev/rules.d/

systemctl daemon-reload
systemctl enable --now katana.service

# The network decision: join a known wifi, or be the access point. Enabled
# but not started here - starting it would change the network underneath
# whoever is running the install, which on a headless Pi means cutting them
# off. It takes effect at the next boot.
systemctl enable katana-net.service katana-net.timer

# The kiosk is deliberately NOT enabled: udev starts it when a screen is
# connected and stops it when one is pulled. Enabling it as well would mean
# a headless boot starting an X server against no display, failing, and
# restarting forever.
systemctl disable katana-kiosk.service 2>/dev/null || true

udevadm control --reload
udevadm trigger --subsystem-match=drm

# Mark the install done, so the first-boot unit (if one was planted) never
# runs again. Harmless when there is no such unit.
date -Iseconds > "$STATE_DIR/.installed"
chown "$APP_USER:$APP_USER" "$STATE_DIR/.installed"
systemctl disable katana-firstboot.service >/dev/null 2>&1 || true

say "Done"
ip=$(hostname -I 2>/dev/null | awk '{print $1}')
cat <<EOF

  Server:  http://${ip:-<pi>}:8000
  Also:    http://$(hostname).local:8000   (if your phone does mDNS)

  systemctl status katana         is it running
  journalctl -u katana -f         what is it doing
  ./deploy/check                  everything at once

  Plug a screen in and the kiosk starts on its own. No reboot.
  Networking (the always-on AP) is not set up yet - that is the next step.

EOF
