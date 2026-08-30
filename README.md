# BOSS Katana MkII — USB MIDI Control

Python control of a **BOSS Katana MkII 100W head** over USB MIDI SysEx,
verified against real hardware.

This is step one of a larger project, so the amp logic lives in a reusable
package (`katana_amp/`) with no printing or prompts — the demo script is just
one caller. A future Raspberry Pi touchscreen UI can import the same module.

## Layout

```
katana_amp/        the library
  katana.py        protocol, address map, parameter tables
  controls.py      friendly helpers - set_gain(75), cry_wah(), ...
  tsl.py           read and load Boss Tone Studio .tsl files
server/
  app.py           FastAPI HTTP + WebSocket API
web/
  index.html       test page - gain, volume, wah, channels
patches/           .tsl patch files
demo.py            command-line demo
run                start the server (API, aux deck and UI on one port)
deploy/            Raspberry Pi install - services, kiosk, see deploy/README.md
vendor/            upstream reference project, for its protocol docs
```

## Setup

Already done in this folder, but to recreate it:

```bash
python3 -m venv venv
./venv/bin/pip install python-rtmidi mido
```

## Running the demo

Amp powered on and connected by USB-B, then:

```bash
./venv/bin/python demo.py
```

This lists the MIDI ports, connects, prints the current patch and tone
settings, then sweeps the **wah from 0 to 100 and back over 10 seconds**.

It leaves the wah **on, at position 0**. Turn it off with
`python -c "from katana_amp.controls import wah_off; wah_off()"`.

**How to confirm the amp responds:** watch the Katana's panel or BOSS Tone
Studio while the demo runs — the gain knob position jumps to maximum and then
returns. If you leave the amp playing, you will hear it. The script also reads
the value back from the amp and prints what the amp itself reports.

Useful options:

```bash
./venv/bin/python demo.py --list                    # list ports and exit
./venv/bin/python demo.py --read-only               # read settings, change nothing
./venv/bin/python demo.py --param volume --value 80 # change a different parameter
./venv/bin/python demo.py --port "KATANA:KATANA MIDI 1 24:0"
```

### MIDI ports

The Katana exposes three ports. **MIDI 1 is the SysEx control port** and is
what the code autodetects; MIDI 2 and 3 do not answer parameter queries.

## Using the module

```python
from katana_amp import Katana

with Katana() as amp:
    print(amp.read_panel())        # patch name, amp type, full tone stack
    print(amp.get_parameter("gain"))
    amp.set_parameter("gain", 75)
```

`Katana()` autodetects the port; pass a name to override. It is a context
manager, so the MIDI ports always close. Errors raise `KatanaError`, and
out-of-range values are rejected before anything is sent to the amp.

For one-line jobs prefer `controls.py` (below). `PARAMETERS` in `katana.py`
lists every named parameter with its valid range.

## Quick helpers

`katana_amp/controls.py` covers every control on the amp. The helpers share one
connection, opened on first use, so there is nothing to pass around:

```python
from katana_amp.controls import *

show_settings()                 # everything the amp is set to, in one view
set_gain(75)
set_amp_type("5150 Drive")
cry_wah()                       # point the pedal at wah, load Cry Wah, switch on
wah_wah(3)                      # rock the treadle - the classic sound
set_reverb_type("Spring")
set_delay_feedback(45)
boost_off()
```

Naming follows the amp's own layout — `set_<section>_<control>`:

| Section | Helpers |
|---|---|
| Amp | `set_gain`, `set_volume`, `set_bass`, `set_middle`, `set_treble`, `set_presence`, `set_tone(...)`, `set_amp_type`, `bright_on/off` |
| Boost | `boost_on/off`, `set_boost_type`, `set_boost_drive`, `set_boost_bottom`, `set_boost_tone`, `set_boost_level`, `boost_solo_on/off`, `set_boost_solo_level` |
| Delay 1 | `delay_on/off`, `set_delay_type`, `set_delay_time` (ms), `set_delay_feedback`, `set_delay_high_cut`, `set_delay_level`, `set_delay_direct_mix` |
| Delay 2 | `delay2_on/off`, `set_delay2_type`, `set_delay2_time` (ms), `set_delay2_feedback`, `set_delay2_high_cut`, `set_delay2_level`, `set_delay2_direct_mix` |
| Noise gate | `noise_gate_on/off`, `set_noise_threshold`, `set_noise_release` |
| Channel LEDs | `get_led`, `set_led`, `get_leds`, `set_leds` |
| Reverb | `reverb_on/off`, `set_reverb_type`, `set_reverb_time`, `set_reverb_level`, `set_reverb_direct_mix` |
| Wah | `cry_wah`, `use_wah`, `wah_on/off`, `set_wah`, `sweep_wah`, `wah_wah`, `set_wah_type`, `set_wah_level`, `set_wah_pedal_min/max` |
| FX slots | `fx1_on/off`, `set_fx1_type`, `fx2_on/off`, `set_fx2_type` |
| EQ | `eq_on/off`, `set_eq_type` |

Every `get_*` has a matching `set_*`. Type setters take a number **or a
name**, matched loosely — `set_boost_type("blues drive")`,
`set_reverb_type("Spring")`, `set_amp_type("jc-120")`. An ambiguous name
tells you what it matched: `set_boost_type("od")` lists the four OD pedals.

Discover what is available:

```python
list_parameters()      # every parameter name with its valid range
list_amp_types()       # 28 amp models
list_boost_types()     # 20 boost/OD pedals
list_effect_types()    # FX slot effects
list_reverb_types()    # 7 reverbs
list_delay_types()     # 9 delays
list_wah_types()       # 6 wah voicings
```

Anything without a dedicated helper is reachable by name:

```python
set_parameter("boost_bottom", 60)
get_parameter("wah_pedal_min")
```

`disconnect()` releases the MIDI port; the next call reopens it. Every
helper still accepts `amp=` if you want to be explicit.

### Graphic EQ

Ten bands, set in dB (-24 to +24, 0 is flat). The amp stores 0–48 with 24
as centre; the helpers do that conversion for you:

```python
set_eq(**{"125hz": 6, "1khz": -4})
get_eq()            # {'31hz': 0, '125hz': 6, '1khz': -4, ...}
reset_eq()          # everything flat
```

Bands: 31hz, 62hz, 125hz, 250hz, 500hz, 1khz, 2khz, 4khz, 8khz, 16khz.

### Effect parameters

Each effect keeps its own settings whatever the FX slots are switched to,
so you can dial one in *before* selecting it:

```python
set_phaser_rate(80)
set_phaser_depth(90)
use_effect(1, "Phaser")     # point FX1 at it and switch on
```

Covered: T Wah, Auto Wah, Compressor, Limiter, Guitar Sim, Wave Synth,
Octave, Phaser, Flanger, Tremolo, Vibrato, Uni-V, Rotary, Slicer, Ring Mod
and Humanizer — each with its own parameters (`set_comp_sustain`,
`set_slicer_pattern`, `set_humanizer_vowel1`, and so on). `list_parameters()`
shows every name with its range.

### Stored patches

The eight sounds behind the CH buttons, readable and writable without
disturbing what is playing:

```python
get_patch_names()           # {1: 'KATANA Mk2', 2: 'kill em', ...}
save_to_patch(3)            # copy the whole live sound into patch 3
read_patch_parameter(2, "gain")
```

`save_to_patch()` copies **everything** — amp, EQ, all effect blocks, both
delays, reverb, wah — about 2.2 KB, the entire patch. It overwrites the
stored channel permanently, so point it somewhere you do not mind losing.

Patches 1–4 are BANK A CH1–4, 6–9 are BANK B CH1–4.

### Channels (tone settings)

Your head stores **8 sounds**: BANK A CH1–4 and BANK B CH1–4, plus PANEL
(the live knob positions). Switching is done with Program Change, which is
what the official manual documents:

```python
select_channel("a1")       # BANK A CH1
select_channel("b3")       # BANK B CH3
select_channel("panel")    # the panel knobs
get_patch_name()           # 'kill em'
```

Programs: `a1`–`a4` = PC 1–4, `panel` = PC 5, `b1`–`b4` = PC 6–9.

### Effect switching by CC

The manual's CC map, the same messages a footswitch sends:

```python
switch_effect("boost", False)     # CC 16
switch_effect("delay", True)      # CC 19
set_expression(64)                # CC 82, external expression pedal
send_cc(21, 127)                  # raw CC - here, effect loop on
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
buttons cycle through. Setting one picks which of that section's three
stored settings is active, and the panel LED follows:

```python
set_led("boost", "red")
set_leds("green")          # all five sections at once
get_leds()                 # {'boost': 'green', 'mod': 'yellow', ...}
```

Sections: `boost`, `mod`, `fx`, `delay`, `reverb`. Colours: `off`, `green`,
`red`, `yellow` (or 0–3).

**These are read-only in practice.** Writing them stores a value that reads
back, but changes nothing on the panel or in the sound — tested on
hardware, and the amp rejects the write outright while in edit mode. They
are a status mirror. To actually change channel, use `select_channel()`
above; the LEDs then follow.

### Getting an actual wah sound

The wah is on the amp's **pedal section**, not an FX slot. That section can
also do pedal-bend, so it has to be pointed at wah first — `cry_wah()` does
all of it (pedal mode → wah, voicing → Cry Wah, switch on). Then the sound
comes from *moving* the treadle:

```python
cry_wah()
wah_wah(3)              # three sweeps up and down
sweep_wah(0, 100)       # one slow sweep
set_wah(50)             # or park it at one position
```

Voicings: Cry Wah, Vo Wah, Fat Wah, Light Wah, 7String Wah, Reso Wah.

### Amp models

The knob picks five, but MIDI reaches all 28:

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
| 8 | JC-120 | 18 | MS1959 I | | |
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
ignores writes, so the writable `volume` helper targets master volume at
`0x60000028` instead.

Delay time is a **two-byte** value (`value = high * 128 + low`) in
milliseconds, 1–2000. `set_delay_time(500)` handles the encoding.

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
bank[0].settings()              # 109 parameters as a dict
bank[0].apply()                 # load it into the amp
```

`apply()` walks the parameters the file defines and sets each one by
name. Verified against three different patch files: 109 parameters, zero
mismatches. It writes to the live area only — follow with
`controls.save_to_patch(n)` to keep one.

There is also `send()`, which copies the raw bytes the way the amp stores
them. It only transfers the amp block correctly: the effect blocks pack
two-byte values and reserved holes in a layout this project has not
worked out, so roughly half those bytes land in the wrong place. Use
`apply()`.

## API server

```bash
./run
```

Then open **http://localhost:8000** for the test page — gain and volume
sliders, wah pedal with a sweep button, and the eight channel buttons. It
follows the amp live over the WebSocket, so changing a channel moves the
sliders.

Serves on `0.0.0.0:8000` so another machine can reach it (use the Pi's
address instead of localhost). Interactive API docs at `/docs`.

| Endpoint | What it does |
|---|---|
| `GET /api/parameters` | Every parameter with range, kind and options — build a UI from this |
| `GET /api/state` | Current value of everything, from cache |
| `GET /api/status` | Whether the amp is answering — cheap enough for a health check |
| `GET /api/parameter/{name}` | One value |
| `PUT /api/parameter/{name}` | `{"value": 75}` |
| `POST /api/channel/{name}` | `a1`–`a4`, `panel`, `b1`–`b4` |
| `GET /api/channels` | Channel list plus stored patch names |
| `GET /api/tsl` | Patch files in `patches/` |
| `POST /api/tsl/{file}/{index}` | Load one patch into the amp |
| `POST /api/refresh` | Re-read the amp (after someone turns a knob) |
| `WS /ws` | Live state pushes, including `{"type":"amp","connected":false}` when the amp comes and goes |

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

The WebSocket sends the whole state on connect, then one message per
change:

```json
{"type": "state",     "values": {...}}
{"type": "parameter", "name": "gain", "value": 75}
{"type": "channel",   "channel": "a1", "values": {...}}
{"type": "patch",     "name": "Southern Solo", "values": {...}}
```

### Notes for the client

The amp is one serial port, so every request goes through a single lock —
concurrent calls are safe but serialised. Reads come from a cache; the amp
is only touched on writes and `POST /api/refresh`.

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
./run --port 9000     # both, somewhere else
./run --no-ui         # the API on its own
```

Then open `http://localhost:8000`, or `http://<this-machine>:8000` from a
phone on the same network — it binds `0.0.0.0`, which is what makes the
second work.

The page is same-origin with the API, so it uses relative URLs and needs no
configuration wherever you open it from. Set `window.KATANA_API_URL` in
`web/index.html` only if you serve the page separately from the API.

The split is in the code rather than the deployment: `server/api.py` is the
amp and knows nothing about a UI, `server/ui.py` is the static mount, and
`server/app.py` is the only place that knows about both.

It talks to the server through `web/js/transport.js` and nothing else —
changes go over the WebSocket, with HTTP as the fallback.

Regenerate the parameter schema after changing `katana.py`:

```bash
./venv/bin/python scripts/generate_schema.py    # writes web/js/schema.js
```

See `web/README.md` for the file-by-file layout.

While a control is being dragged the store *holds* that parameter, so an
update arriving from the amp cannot yank it out from under a finger.

Switching channel and loading a patch are slow operations — two to three
seconds of MIDI, during which nothing changes and then everything changes
at once. The store exposes `busy` for those: a progress bar runs and the
controls that would queue another one are disabled.

`src/lib/katana/generated.ts` is written by `scripts/generate_schema.py`.
Do not edit it: the amp's enum numbering is sparse, and hand-maintaining
it in two languages is how "Phaser" ends up loading Octave.

## Sources

- [snhirsch/katana-midi-bridge](https://github.com/snhirsch/katana-midi-bridge)
  — first-generation protocol groundwork (vendored in `vendor/`).
- [Katana MkII MIDI Address Map, VGuitarForums](https://www.vguitarforums.com/smf/index.php?topic=27749.0)
  — the MkII address map. Its listed identity reply matches this amp exactly.
- [katana-dev/docs](https://github.com/katana-dev/docs) — the 28 amp type table.

Every address used here was re-verified by reading and writing to the amp.
