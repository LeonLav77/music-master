# Kiosk: the Pi as a device

With the touch screen plugged in, the Pi boots to the Katana logo and then
the control surface, fullscreen. No desktop, no browser bar, no boot text.
Without the screen it is the same headless server as before.

## Installing

On the Pi, from the repo:

```bash
cd ~/katana
git pull
sudo bash deploy/install.sh
sudo reboot
```

`install.sh` can be run any number of times. Run it again after a pull that
changes anything in `deploy/`.

## What happens at boot

```
firmware ......... rainbow square        hidden: disable_splash=1 in config.txt
kernel ........... text and raspberries  hidden: quiet, logo.nologo, console=tty3
Plymouth ......... the Katana logo       plymouth/katana/
music-master ..... the server starts     music-master.service
kiosk-ready ...... waits for :8000,      kiosk-ready.service
                   quits Plymouth
kiosk ............ cage + Chromium       kiosk.service, kiosk-browser
```

| File | What it is |
| --- | --- |
| `install.sh` | Installs the packages, the logo, the boot settings and both services |
| `music-master.service` | The server, on boot - the same `./run` as by hand |
| `kiosk-ready.service` | Holds the logo up until the server answers, then quits Plymouth (as root - see below) |
| `kiosk.service` | cage on tty1, the Pi's own screen. Skipped when no screen is plugged in |
| `kiosk-browser` | Chromium with every bit of browser switched off. `SCALE` sets the page size |
| `plymouth/katana/` | The boot logo: theme file, script, `logo.png` and the flickering `glow.png` |

**cage** is a Wayland compositor - the program that owns the screen and the
touch panel - that runs exactly one app, fullscreen. There is nothing behind
it to fall back to: if Chromium closes, cage closes, and systemd starts them
again two seconds later.

**The logo stays up until the page is ready.** `kiosk-ready.service` is
ordered before `plymouth-quit.service` and `kiosk.service`, waits for the
server to answer, and then quits Plymouth with `--retain-splash`, which
leaves the logo on screen until Chromium draws over it. It is a separate
unit because Plymouth only listens to root: run from `kiosk.service` (as
leon, on tty1) `plymouth quit` hangs, and the screen stays black until the
start times out two minutes later.

**The page knows it is the kiosk** by the `?kiosk` in its URL: `app.js` adds
`.kiosk` to `<html>`, and `app.css` hides the cursor and turns off text
selection and the long-press menu. A phone gets none of that.

## Changing things

- **Page size** - `SCALE` in `kiosk-browser`. Below 1 shrinks the page; the PC
  layout needs 1000 CSS pixels, so a 1024px screen fits it at 1 and gives it
  more room at 0.8. Then `sudo systemctl restart kiosk`.
- **The logo** - replace `logo.png` and `glow.png` (same size, the glow drawn
  where the bulb is), then run `install.sh` again: the logo lives inside the
  initramfs, which it rebuilds.

## When something is wrong

```bash
systemctl status kiosk           # running, skipped (no screen) or failing?
journalctl -u kiosk -b           # its output since this boot
sudo systemctl restart kiosk     # reload the page
sudo systemctl stop kiosk        # the screen goes back to black
```

`install.sh` keeps the boot files as they were before it first ran, as
`cmdline.txt.before-kiosk` and `config.txt.before-kiosk` in `/boot/firmware`.
