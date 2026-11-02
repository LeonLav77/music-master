#!/usr/bin/env bash
# Set the Pi up as a kiosk: the server on boot, the Katana logo while it
# boots, then the control surface fullscreen on the touch screen.
#
#   cd ~/katana && sudo bash deploy/install.sh
#
# Safe to run again - after a git pull, run it to pick up changed
# services or a new logo. Every step checks before it changes anything.


# Stavi strict mode
set -euo pipefail

# Stavi se u tocan repo
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY="$REPO/deploy"
BOOT=/boot/firmware
THEMES=/usr/share/plymouth/themes

# Provjeri pokrece li sudo
if [[ $EUID -ne 0 ]]; then
  echo "Run it with sudo: sudo bash deploy/install.sh" >&2
  exit 1
fi

step() { echo; echo "==> $*"; }

# Potrebni paketi
step "Packages: cage (the one-app screen), chromium, plymouth (the boot logo)"
apt-get update
apt-get install -y cage chromium plymouth


# Ubaci logo dok se boot-a
step "Boot logo: the Katana theme"
install -D -m 644 -t "$THEMES/katana" "$DEPLOY"/plymouth/katana/*
# -R rebuilds the initramfs, the small early-boot system the logo is
# shown from - the theme has to be inside it to appear that early.
plymouth-set-default-theme -R katana


# Izbaci kernel poruke i splash sa ekrana
step "Boot text: hide the rainbow square, raspberries, kernel messages, cursor"
[[ -e $BOOT/cmdline.txt.before-kiosk ]] || cp "$BOOT/cmdline.txt" "$BOOT/cmdline.txt.before-kiosk"
[[ -e $BOOT/config.txt.before-kiosk ]] || cp "$BOOT/config.txt" "$BOOT/config.txt.before-kiosk"

# Izbaci errore na tty3 umjesto na ekran
sed -i 's/\bconsole=tty1\b/console=tty3/' "$BOOT/cmdline.txt"
for argument in quiet splash plymouth.ignore-serial-consoles logo.nologo vt.global_cursor_default=0; do
  grep -qw -- "$argument" "$BOOT/cmdline.txt" || sed -i "s/\$/ $argument/" "$BOOT/cmdline.txt"
done

# Ugasi splash ekran od Raspberry Pi-a
grep -qx 'disable_splash=1' "$BOOT/config.txt" || printf '\n[all]\ndisable_splash=1\n' >> "$BOOT/config.txt"


# Upali potrebne servise
step "Services: the server, and the kiosk on the screen"
install -m 644 "$DEPLOY/music-master.service" "$DEPLOY/kiosk-ready.service" "$DEPLOY/kiosk.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable music-master.service kiosk-ready.service kiosk.service
# Pi pokusava pokazati sign up screen na tty1 ali mi zelimo prikazati kiosk
systemctl disable getty@tty1.service


echo
echo "Done. Reboot with the screen plugged in to see it: sudo reboot"
