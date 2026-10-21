# BOSS Katana MkII — USB MIDI Control

Control a **BOSS Katana MkII 100W head** over USB MIDI SysEx, verified
against real hardware: a Python library for the amp, and a web control
surface on top of it that runs on a Raspberry Pi and works from a phone.

## Layout

```
katana_amp/        the library - no printing, no prompts, reusable
  katana.py        the MIDI protocol and the Katana connection class
  param.py         Param: every setting, with its address, range and kind
  kind.py          Kind: what sort of control a setting is (knob, switch, dropdown)
  controls.py      the shared connection, get/set_parameter, wah, channels
  tsl.py           read and load BOSS Tone Studio .tsl files
server/            FastAPI app: amp API and the UI on one port
  app.py           creates the app and plugs the parts in
  amp.py           the link to the amp: lock, cache, reconnect loop, broadcast
  routes.py        the HTTP endpoints
  live.py          the WebSocket: knob changes and channel switches
  meter.py         the input meter: guitar loudness from the amp's USB audio
web/               the control surface - plain HTML, CSS and JS, no build step
docs/
  CONTROLS.md      every parameter the amp exposes, with ranges
  TSL_FORMAT.md    the .tsl patch file format, reverse-engineered
run                start the server
requirements.txt   Python dependencies
```

`patches/` (Tone Studio files) is created as you use it and is not part
of the code.

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

On a Pi, `python-rtmidi` compiles from source and needs
`python3-dev build-essential libasound2-dev` installed first.

## Running

Amp powered on and connected by USB-B, then:

```bash
./run
```

and open `http://<this machine>:8000`. Or drive the amp from Python
directly - see below.

### MIDI ports

The Katana exposes three ports. **MIDI 1 is the SysEx control port** and is
what the code autodetects; MIDI 2 and 3 do not answer parameter queries.

## Using it from Python

```python
from katana_amp.controls import get_parameter, set_parameter
from katana_amp.param import Param

set_parameter(Param.GAIN, 75)
get_parameter(Param.REVERB_LEVEL)          # 38
set_parameter(Param.AMP_TYPE, 24)          # 5150 Drive
set_parameter(Param.EQ_BAND_1KHZ, -4)      # EQ in dB, -24 to +24
set_parameter(Param.DELAY_TIME, 500)       # milliseconds
```

Everything shares one connection to the amp, opened on first use, so there
is nothing to pass around. `disconnect()` releases the MIDI port; the next
call reopens it. Errors raise `KatanaError`, and out-of-range values are
rejected before anything is sent to the amp.

### Every setting is a `Param`

`Param` in `katana_amp/param.py` is a backed enum, like Laravel's: each
case is a readable name, and its methods answer questions about it. Each
method uses `match`, listing the exceptions and ending in a default
`case _` for the common answer (a 0-100 knob, one byte, writable).

```python
Param("gain")                # Param.GAIN - like Laravel's Param::from('gain')
Param.GAIN.value             # 'gain' - what the browser sends
Param.GAIN.address()         # 0x60000022
Param.GAIN.kind()            # Kind.RANGE - RANGE is a knob, TOGGLE a switch, ENUM a dropdown
Param.GAIN.range()           # (0, 100)
Param.AMP_TYPE.options()     # {0: 'Natural Clean', ..., 8: 'JC-120', ...}
Param.KNOB_VOLUME.is_writable()   # False
Param.EQ_BAND_1KHZ.unit()    # 'dB'
list(Param)                  # all 154 of them
```

Adding a setting means a new case, its arm in `address()`, and an arm in
any method where it is not the default.

Values are always in real units. The EQ bands are dB: the amp stores them
0–48 with 24 as flat, and `Param` converts. Delay times are milliseconds,
stored by the amp as two bytes. `docs/CONTROLS.md` lists every setting.

Each effect keeps its own settings whatever the FX slots are switched to,
so you can dial one in *before* selecting it:

```python
set_parameter(Param.PHASER_RATE, 80)
set_parameter(Param.FX1_TYPE, 19)          # Phaser, into slot 1
set_parameter(Param.FX1_SWITCH, 1)
```

### Channels and stored patches

Your head stores **8 sounds**: BANK A CH1–4 and BANK B CH1–4, plus PANEL
(the live knob positions). Switching is done with Program Change, which is
what the official manual documents:

```python
from katana_amp.controls import get_patch_names, save_to_patch, select_channel

select_channel("a1")        # BANK A CH1
select_channel("panel")     # the panel knobs
get_patch_names()           # {1: 'KATANA Mk2', 2: 'kill em', ...}
save_to_patch(3)            # copy the whole live sound into patch 3
```

Programs: `a1`–`a4` = PC 1–4, `panel` = PC 5, `b1`–`b4` = PC 6–9.

The amp keeps the channel it is on at `00 01 00 00`, as a two-byte program
number counted from 0 (B2 reads `[0, 6]`). The server reads it with every
refresh, so the UI shows the real channel. The amp does **not** announce
channel changes made with its own CH buttons; press Resync to pick those up.

`save_to_patch()` copies **everything** — amp, EQ, all effect blocks, both
delays, reverb, wah — about 2.2 KB, the entire patch. It overwrites the
stored channel permanently, so point it somewhere you do not mind losing.

### Footswitch messages

The manual's CC map, the same messages a footswitch sends
(0–63 = off, 64–127 = on):

```python
from katana_amp.controls import send_cc

send_cc(16, 0)       # boost off
send_cc(19, 127)     # delay on
```

| CC | Effect | | CC | Effect |
|---|---|---|---|---|
| 16 | Boost | | 20 | Reverb |
| 17 | Mod | | 21 | Effect loop |
| 18 | FX | | 80–82 | Expression pedals |
| 19 | Delay | | 83–84 | GA-FC footswitches |

The amp's receive channel is CH 1 from the factory (set by holding a CH
button while powering on). Pass `midi_channel=` to `Katana()` if yours
differs.

### Channel LEDs

Each effect section has a colour channel — the green/red/yellow the panel
buttons cycle through. `LED_BOOST`, `LED_MOD`, `LED_FX`, `LED_DELAY` and
`LED_REVERB` report which one is active:

```python
get_parameter(Param.LED_BOOST)         # 2
Param.LED_BOOST.options()[2]           # 'red'
```

**They are read-only** (`is_writable()` is `False`). Writing them stores a value
that reads back, but changes nothing on the panel or in the sound — tested
on hardware. To actually change channel, use `select_channel()`; the LEDs
then follow.

### Getting an actual wah sound

The wah is on the amp's **pedal section**, not an FX slot. That section can
also do pedal-bend, so it has to be pointed at wah first. Then the sound
comes from *moving* the treadle:

```python
set_parameter(Param.PEDAL_TYPE, 0)     # the pedal section does wah...
set_parameter(Param.WAH_TYPE, 0)       # ...as a Cry Wah
set_parameter(Param.PEDAL_SWITCH, 1)

set_parameter(Param.WAH_POSITION, 80)  # move the treadle
```

Voicings: Cry Wah, Vo Wah, Fat Wah, Light Wah, 7String Wah, Reso Wah.

### Amp models

The front-panel knob picks five, but MIDI reaches all of them:

| # | Model | # | Model | # | Model |
|---|---|---|---|---|---|
| 0 | Natural Clean | 10 | Pro Crunch | 20 | R-Fire Vintage |
| 1 | Full Range | 11 | Tweed | 21 | R-Fire Modern |
| 2 | Combo Crunch | 12 | Deluxe Crunch | 22 | T-Amp Lead |
| 3 | Stack Crunch | 13 | VO Drive | 23 | SLDN |
| 4 | HiGain Stack | 14 | VO Lead | 24 | 5150 Drive |
| 5 | Power Drive | 15 | Match Drive | 25 | Custom |
| 6 | Extreme Lead | 16 | BG Lead | 26 | BGNR UB |
| 7 | Core Metal | 17 | BG Drive | 27 | Orng RB |
| 8 | JC-120 | 18 | MS1959 I | 28–32 | MkII models, unnamed |
| 9 | Clean Twin | 19 | MS1959 I+II | | |

## Protocol notes

Messages are `F0 41 00 00 00 00 33 <op> <addr:4> <payload> <cksum> F7`,
where op `0x11` queries and `0x12` sets, with a Roland 7-bit checksum over
address + data.

**The MkII is not the amp the `katana-midi-bridge` docs describe.** That
project documents the first-generation Katana, whose `00 00 04 xx` front
panel addresses this amp ignores completely — no error, just silence. The
MkII keeps its live state in a "temporary patch" area at `0x60000000`, with
user patches 1-9 mirroring the same layout from `0x10000000` up.

Verified addresses (read *and* written on a MkII 100W head):

| Address | Parameter | Range |
|---|---|---|
| `0x60000000` | Patch name, 16 ASCII bytes | — |
| `0x60000021` | Amp type | 0–27 |
| `0x60000022` | Gain | 0–100 |
| `0x60000023` | Volume knob (read-only) | 0–100 |
| `0x60000024` | Bass | 0–100 |
| `0x60000025` | Middle | 0–100 |
| `0x60000026` | Treble | 0–100 |
| `0x60000027` | Presence | 0–100 |
| `0x60000028` | Master volume (`volume`) | 0–100 |
| `0x60000029` | Bright | 0/1 |
| `0x60000100` / `0x60000101` | FX1 switch / type | 0/1, 0–38 |
| `0x60000300` / `0x60000301` | FX2 switch / type | 0/1, 0–38 |
| `0x60000010`–`0x60000018` | Boost: switch, type, drive, bottom, tone, solo, level | |
| `0x60000040`/`0x60000041` | EQ switch / type | |
| `0x60000500`–`0x60000507` | Delay 1: switch, type, time, feedback, high cut, level, direct | |
| `0x60000520`–`0x60000527` | Delay 2: same layout as delay 1 | |
| `0x60000566`–`0x60000568` | Noise suppressor: switch, threshold, release | |
| `0x6000065D`–`0x60000661` | Channel LEDs: boost, mod, fx, delay, reverb (read-only) | 0–3 |
| `0x6000004D`–`0x60000057` | Graphic EQ: 10 bands + level | 0–48 |
| `0x60000203`–`0x6000022A` | Effect blocks: phaser, flanger, tremolo, vibrato, Uni-V | |
| `0x10000000` + `n * 0x10000` | Stored patches 1–9, same layout as live | |
| `0x60000540`–`0x60000549` | Reverb: switch, type, time, level, direct | |
| `0x60000550`–`0x60000557` | Pedal wah: switch, mode, voicing, position, min/max, level | |

`0x60000023` reports the position of the physical volume knob and silently
ignores writes, so the writable `volume` setting is master volume at
`0x60000028` instead.

Delay time is a **two-byte** value (`value = high * 128 + low`) in
milliseconds, 1–2000. `set_parameter(Param.DELAY_TIME, 500)` handles the encoding.

The type *names* for delay and reverb come from the first-generation docs
and are unverified on the MkII — the amp reports numbers only. The numbers
are correct; a label may not be. Unknown values print as `type 10`.

Still unmapped: Pitch Shifter and Harmonist (`0x6000014A`–`0x6000017B`),
which carry per-voice interval tables rather than plain knobs, and the
AC Processor. FX2 mirrors FX1 at +0x200 throughout.

Not reachable by MIDI at all (physical switches, per the official manual):
POWER CONTROL, CAB RESONANCE, TAP tempo, bank A/B hold-switch, STEREO
EXPAND.

## Troubleshooting

- **No Katana port found** — check `lsusb` for `Roland Corp. KATANA` and
  confirm the amp is on. On Linux you may need to be in the `audio` group.
- **No reply from the amp** — make sure you are on MIDI 1, and close BOSS
  Tone Studio if it is holding the port.

## Tone Studio patches

`.tsl` files exported from BOSS Tone Studio can be read and loaded:

```python
from katana_amp import tsl

bank = tsl.load("pantera.tsl")
tsl.describe("pantera.tsl")     # summary of every patch in the file
bank[0].settings()              # {Param: value}, 109 settings
bank[0].apply()                 # load it into the amp
```

`apply()` walks the parameters the file defines and sets each one by
name. Verified against three different patch files: 109 parameters, zero
mismatches. It writes to the live area only — follow with
`controls.save_to_patch(n)` to keep one.

## API server

```bash
./run
```

Then open **http://localhost:8000** for the control surface — amp knobs,
effect pedals, graphic EQ, wah treadle and channels. It follows the amp live over the WebSocket, so changing a channel
moves the knobs.

Serves on `0.0.0.0:8000` so another machine can reach it (use the Pi's
address instead of localhost). Interactive API docs at `/docs`.

| Endpoint | What it does |
|---|---|
| `GET /api/parameters` | Every parameter with range, kind and options — build a UI from this |
| `GET /api/status` | Whether the amp is answering — cheap enough for a health check |
| `GET /api/channels` | Channel list plus stored patch names |
| `GET /api/tsl` | Patch files in `patches/` |
| `POST /api/tsl/{file}/{index}` | Load one patch into the amp |
| `POST /api/refresh` | Re-read the amp (after someone turns a knob) |
| `POST /api/patch/{number}` | Save the live sound into a stored channel |
| `POST /api/cc/{control}` | Send a raw Control Change, as a footswitch would |
| `WS /ws` | Live changes both ways: knob values and channel switches in, state pushes out |

The schema drives the client, so there is no hardcoded list of fields on
either side:

```json
{"name": "gain", "group": "amp", "kind": "range", "min": 0, "max": 100, "writable": true}
{"name": "amp_type", "group": "amp", "kind": "enum", "options": {"24": "5150 Drive", ...}}
{"name": "eq_band_1khz", "group": "eq", "kind": "range", "min": -24, "max": 24, "unit": "dB"}
```

`kind` is `range`, `toggle` or `enum`. EQ bands are exposed in dB and
delay times in ms, converted at the edge. `writable: false` marks the
parameters the amp reports but ignores writes to, so the UI can grey them
out rather than offer a control that does nothing.

Setting a parameter and switching channel happen over the WebSocket only:

```json
{"type": "set",     "name": "gain", "value": 75}
{"type": "channel", "name": "b2"}
```

It sends the whole state on connect, then one message per change:

```json
{"type": "amp",       "connected": true}
{"type": "state",     "values": {...}}
{"type": "parameter", "name": "gain", "value": 75}
{"type": "channel",   "channel": "a1", "values": {...}}
{"type": "patch",     "name": "Southern Solo", "values": {...}}
{"type": "patches",   "names": {"1": "IRON BELL", ...}}
```

### Notes for the client

The amp is one serial port, so every request goes through a single lock —
concurrent calls are safe but serialised. A page that connects gets the
state from a cache; the amp is re-read on a refresh, a channel switch and
when it reconnects.

Nothing tells the server when someone turns a physical knob. Call
`/api/refresh` when you want the truth, or accept that the UI drifts until
the next channel change.

## Interface

`web/` is the control surface: plain HTML, hand-written CSS and ES modules
with [Alpine](https://alpinejs.dev) for reactivity. No build step, no
dependencies to install.

One process serves both the API and the page:

```bash
./run                 # API and UI on :8000
```

Then open `http://localhost:8000`, or `http://<this-machine>:8000` from a
phone on the same network — it binds `0.0.0.0`, which is what makes the
second work.

The page is same-origin with the API, so it needs no configuration
wherever you open it from.

`server/amp.py` is the link to the amp and knows nothing about a UI;
`server/routes.py` (HTTP) and `server/live.py` (WebSocket) are built on it,
and `server/app.py` plugs them in and serves `web/` alongside them.

It talks to the server through `web/js/transport.js` and nothing else —
changes go over the WebSocket, with HTTP as the fallback.

The UI fetches the parameter schema from `/api/parameters` when it loads,
so a change to `param.py` reaches it after a server restart.

See `web/README.md` for the file-by-file layout.

While a control is being dragged the store *holds* that parameter, so an
update arriving from the amp cannot yank it out from under a finger.

Switching channel and loading a patch are slow operations — two to three
seconds of MIDI, during which nothing changes and then everything changes
at once. The store exposes `busy` for those: a progress bar runs and the
controls that would queue another one are disabled.

The parameter tables live only in Python. The amp's enum numbering is
sparse, and hand-maintaining it in two languages is how "Phaser" ends up
loading Octave.

## Sources

- [snhirsch/katana-midi-bridge](https://github.com/snhirsch/katana-midi-bridge)
  — first-generation protocol groundwork.
- [Katana MkII MIDI Address Map, VGuitarForums](https://www.vguitarforums.com/smf/index.php?topic=27749.0)
  — the MkII address map. Its listed identity reply matches this amp exactly.
- [katana-dev/docs](https://github.com/katana-dev/docs) — the 28 amp type table.

Every address used here was re-verified by reading and writing to the amp.
