# Putting this on a Raspberry Pi

The goal: **power on and it serves the amp. Plug a screen in and the surface
appears.** Nothing else to do, nothing to type.

Everything here has to be installed **at home, on wifi**. At a venue the Pi is
its own island with no internet, so a missing package cannot be fixed there.

---

## 1. Flash the card

Raspberry Pi Imager, **Raspberry Pi OS Lite (64-bit)**. Lite, not Desktop — the
kiosk brings its own minimal X, and a full desktop just eats RAM you will want
back on a Zero 2 W.

Before writing, open the settings (the gear icon) and set:

| Setting | Value | Why |
| --- | --- | --- |
| Hostname | `gitra` | makes `http://gitra.local:8000` work |
| Enable SSH | yes, password or key | the only way in on a headless Pi |
| Username | your own | not `katana`; the installer makes that one |
| Wifi | your home network | needed for the install |
| Locale/keyboard | yours | saves a surprise if you ever attach a keyboard |

## 2. Install — no SSH needed

With the card still in your laptop, point `bootstrap` at its **boot**
partition (the small FAT32 one, usually mounted as `bootfs`):

```bash
./deploy/bootstrap /media/$USER/bootfs
```

That copies the project onto the card and arranges for it to install itself.
Put the card in the Pi, power it on, and wait — several minutes, mostly
compiling `python-rtmidi`, which has no ARM wheel.

It needs the wifi you set in Imager: the install pulls from apt and PyPI. This
is the one step that cannot happen at a venue.

When it finishes the server is running and enabled at boot. Open
`http://gitra.local:8000` from your phone on the same wifi.

**If it seems dead**, power off, put the card back in your laptop, and read
`katana-install.log` on the boot partition. Every failure says what to do
about it. That log is written to the FAT32 partition on purpose — it is the
only thing you can read without a working Pi.

<details>
<summary>Doing it by hand instead</summary>

```bash
ssh <you>@gitra.local
sudo apt update && sudo apt install -y git
git clone <your repo> katana && cd katana
sudo ./deploy/install.sh
./deploy/check
```

Same installer. `bootstrap` only automates getting it onto the Pi and running
it once.
</details>

### About that address

`.local` is mDNS, not your router's DNS — the Pi answers for its own name,
peer to peer. That is why it will keep working on the Pi's own access point
later, where there is no DNS server at all.

Two things worth knowing before you decide it is broken:

- **Android resolves `.local` inconsistently.** iOS and macOS are reliable;
  Android varies by version. If yours does not, use the IP — `./deploy/check`
  prints it, and so does the end of the install.
- Once the access point is set up (next step), the Pi runs its own DNS on it,
  so **bare `http://gitra:8000`** will work when connected to the amp's own
  network. On home wifi you still need `gitra.local`, because there your
  router does the resolving and it has never heard of the Pi.

## 3. Plug a screen in

Nothing to configure. A udev rule watches the DRM connectors and starts the
kiosk when a display appears, stops it when one is pulled. No reboot.

If the picture is sideways, or touch lands in the wrong place, set the rotation
in `/etc/default/katana-kiosk`:

```sh
KIOSK_ROTATE=left      # or right, inverted, normal
```

then `sudo systemctl restart katana-kiosk`. The touch digitiser is rotated to
match automatically — rotating the picture alone would leave taps landing in
the wrong corner.

---

## What is installed

| Path | What |
| --- | --- |
| `/opt/katana` | the app, its venv, `patches/` and `tracks/` |
| `/var/lib/katana` | service user's home, Chromium's profile |
| `/etc/systemd/system/katana.service` | the server — enabled, starts at boot |
| `/etc/systemd/system/katana-kiosk.service` | the screen — **not** enabled, udev starts it |
| `/etc/udev/rules.d/99-katana-display.rules` | the hot-plug trigger |
| `/boot/firmware/katana/` | the copy `bootstrap` put there, and the install log |

The kiosk is deliberately not enabled. If it were, a headless boot would start
an X server against no display, fail, and restart for ever. udev is what
decides, because udev is what knows whether a screen is there.

## Design notes

**The server never depends on the screen.** Separate units with no ordering
between them. The kiosk can fail, X can fail, the panel can be garbage — the
server stays up and your phone still works. That is the interface you cannot
afford to lose.

**The server never depends on the amp.** It starts with the amp off, retries
every 2s, and reconnects on its own when the amp appears. Powering the rig up
in any order is fine.

**It restarts for ever.** `StartLimitIntervalSec=0` on both units. The default
gives up after 5 failures in 10s, which would leave the thing dead until you
found a laptop.

## When something is wrong

```bash
./deploy/check                    everything at once, with what to do
systemctl status katana           is the server up
journalctl -u katana -f           what it is doing now
journalctl -u katana-kiosk -n 50  why the screen is blank
```

**The amp does not need the Pi.** If all of this fails at a gig, the Katana is
still an amp — the Pi only changes settings over MIDI. Nothing here can leave
you without sound.

## Still to come

Networking. Right now the Pi only joins the wifi it was flashed with, so it is
reachable at home and nowhere else. The always-on access point — so your phone
finds it at a venue with no wifi at all — is the next piece.
