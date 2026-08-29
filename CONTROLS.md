# Katana MkII — Control Reference

Every control this project can reach, for designing the web UI.
**154 parameters**, generated from the live schema
(`GET /api/parameters`) so it cannot drift from the code.

Each entry is one of three kinds, which is all the UI needs to render it:

| Kind | Widget |
|---|---|
| `range` | slider |
| `toggle` | switch |
| `enum` | dropdown / segmented control |

---

## Amp

The main knob row — the core of any patch.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `amp_type` | enum | enum — 33 options |  |
| `bass` | range | 0 … 100 |  |
| `bright` | toggle | on / off |  |
| `gain` | range | 0 … 100 |  |
| `knob_volume` | range | 0 … 100 | **read-only** |
| `middle` | range | 0 … 100 |  |
| `presence` | range | 0 … 100 |  |
| `treble` | range | 0 … 100 |  |
| `volume` | range | 0 … 100 |  |

**Amp models** (33). Only five are reachable from the front panel;
the rest are MIDI-only, which is worth showing off in the UI.

`0` Natural Clean · `1` Full Range · `2` Combo Crunch  
`3` Stack Crunch · `4` HiGain Stack · `5` Power Drive  
`6` Extreme Lead · `7` Core Metal · `8` JC-120  
`9` Clean Twin · `10` Pro Crunch · `11` Tweed  
`12` Deluxe Crunch · `13` VO Drive · `14` VO Lead  
`15` Match Drive · `16` BG Lead · `17` BG Drive  
`18` MS1959 I · `19` MS1959 I+II · `20` R-Fire Vintage  
`21` R-Fire Modern · `22` T-Amp Lead · `23` SLDN  
`24` 5150 Drive · `25` Custom · `26` BGNR UB  
`27` Orng RB · `28` MkII amp 28 · `29` MkII amp 29  
`30` MkII amp 30 · `31` MkII amp 31 · `32` MkII amp 32

Values 28–32 are MkII-only and appear in no public documentation. They are
real — Tone Studio patches use them — but unnamed here.

---

## Boost / Overdrive

A modelled pedal in front of the amp.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `boost_bottom` | range | 0 … 100 |  |
| `boost_direct_mix` | range | 0 … 100 |  |
| `boost_drive` | range | 0 … 100 |  |
| `boost_level` | range | 0 … 100 |  |
| `boost_solo_level` | range | 0 … 100 |  |
| `boost_solo_switch` | toggle | on / off |  |
| `boost_switch` | toggle | on / off |  |
| `boost_tone` | range | 0 … 100 |  |
| `boost_type` | enum | enum — 20 options |  |

**Pedal models** (20):

`0` Mid Boost · `1` Clean Boost · `2` Treble Boost  
`3` Crunch OD · `4` Natural OD · `5` Warm OD  
`6` Fat DS · `8` Metal DS · `9` Oct Fuzz  
`10` Blues Drive · `11` Overdrive · `12` T-Scream  
`13` Turbo OD · `14` Distortion · `15` Rat  
`16` Guv DS · `17` DST+ · `18` Metal Zone  
`19` '60s Fuzz · `20` Muff Fuzz

---

## Delay

Two independent delay engines with identical controls. The second is the
same names prefixed `delay2_`.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `delay_direct_mix` | range | 0 … 100 |  |
| `delay_feedback` | range | 0 … 100 |  |
| `delay_high_cut` | range | 0 … 14 |  |
| `delay_level` | range | 0 … 120 |  |
| `delay_switch` | toggle | on / off |  |
| `delay_time` | range | 1 … 2000 ms |  |
| `delay_type` | enum | enum — 5 options |  |

**Delay types** (5): `0` Digital · `6` Reverse · `7` Analog · `8` Tape Echo · `9` Modulate

`delay_time` is in **milliseconds, 1–2000** — a real unit, not 0–100.

---

## Reverb

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `reverb_direct_mix` | range | 0 … 100 |  |
| `reverb_level` | range | 0 … 100 |  |
| `reverb_switch` | toggle | on / off |  |
| `reverb_time` | range | 0 … 99 |  |
| `reverb_type` | enum | enum — 7 options |  |

**Reverb types** (7): `0` Room · `1` Hall · `2` Plate · `3` Spring · `4` Modulate · `5` Reverb+Delay · `6` Fast Decay

---

## Wah / Expression pedal

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `pedal_switch` | toggle | on / off |  |
| `pedal_type` | enum | enum — 3 options |  |
| `wah_direct_mix` | range | 0 … 100 |  |
| `wah_level` | range | 0 … 100 |  |
| `wah_pedal_max` | range | 0 … 100 |  |
| `wah_pedal_min` | range | 0 … 100 |  |
| `wah_position` | range | 0 … 100 |  |
| `wah_type` | enum | enum — 6 options |  |

**Voicings** (6): `0` Cry Wah · `1` Vo Wah · `2` Fat Wah · `3` Light Wah · `4` 7String Wah · `5` Reso Wah

**Pedal modes** (3): `0` Wah · `1` Pedal Bend · `2` Wah 95E

`wah_position` is the treadle. It is the one control that exists to be
*swept* rather than set — worth a large vertical or rotary widget. A
sweep must be driven server-side in one request, not stepped from the
browser.

---

## Graphic EQ

Ten bands, **−24 … +24 dB**, 0 is flat. The amp stores 0–48 internally;
the API converts, so the UI works in dB.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `eq_band_125hz` | range | -24 … 24 dB |  |
| `eq_band_16khz` | range | -24 … 24 dB |  |
| `eq_band_1khz` | range | -24 … 24 dB |  |
| `eq_band_250hz` | range | -24 … 24 dB |  |
| `eq_band_2khz` | range | -24 … 24 dB |  |
| `eq_band_31hz` | range | -24 … 24 dB |  |
| `eq_band_4khz` | range | -24 … 24 dB |  |
| `eq_band_500hz` | range | -24 … 24 dB |  |
| `eq_band_62hz` | range | -24 … 24 dB |  |
| `eq_band_8khz` | range | -24 … 24 dB |  |
| `eq_level` | range | 0 … 48 |  |
| `eq_switch` | toggle | on / off |  |
| `eq_type` | toggle | on / off |  |

Band order for a fader row: 31Hz · 62 · 125 · 250 · 500 · 1k · 2k · 4k ·
8k · 16k.

This is where a tone lives. The Pantera patch, for reference, is
+14 / +14 / +12 / −6 / −12 / −15 / −7 / +8 / +10 / +11 — a deep mid scoop
with boosted extremes.

---

## Noise gate

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `noise_suppressor_release` | range | 0 … 100 |  |
| `noise_suppressor_switch` | toggle | on / off |  |
| `noise_suppressor_threshold` | range | 0 … 100 |  |

---

## Effect slots

Two slots, each loading one of **19 effects**:

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `fx1_switch` | toggle | on / off |  |
| `fx1_type` | enum | enum — 19 options |  |
| `fx2_switch` | toggle | on / off |  |
| `fx2_type` | enum | enum — 19 options |  |

**Effects** (19):

`0` T Wah · `1` Auto Wah · `2` Pedal Wah  
`3` Comp · `4` Limiter · `6` Graphic EQ  
`7` Parametric EQ · `9` Guitar Sim · `10` Slow Gear  
`12` Wave Synth · `14` Octave · `15` Pitch Shifter  
`16` Harmonist · `18` AC Processor · `19` Phaser  
`20` Flanger · `21` Tremolo · `22` Rotary  
`23` Uni-V

### Per-effect parameters

Behind those slots sit **84 parameters** — every
effect's own knobs. They are addressable whatever the slots are set to,
so an effect can be dialled in before it is selected.

| Effect | Params | Controls |
|---|---|---|
| **Auto Wah** | 7 | `depth`, `direct_mix`, `frequency`, `level`, `mode`, `peak`, `rate` |
| **Comp** | 5 | `attack`, `level`, `sustain`, `tone`, `type` (0–6) |
| **Flanger** | 7 | `depth`, `direct_mix`, `level`, `low_cut` (0–10), `manual`, `rate`, `resonance` |
| **Guitar Sim** | 4 | `high`, `level`, `low`, `type` (0–7) |
| **Humanizer** | 8 | `depth`, `level`, `manual`, `mode`, `rate`, `sens`, `vowel1` (0–4), `vowel2` (0–4) |
| **Limiter** | 6 | `attack`, `level`, `ratio` (0–17), `release`, `threshold`, `type` (0–2) |
| **Octave** | 3 | `direct_mix`, `level`, `range` (0–3) |
| **Phaser** | 8 | `depth`, `direct_mix`, `level`, `manual`, `rate`, `resonance`, `step_rate`, `type` (0–3) |
| **Ring Mod** | 4 | `direct_mix`, `frequency`, `level`, `mode` |
| **Rotary** | 3 | `depth`, `level`, `rate_fast` |
| **Slicer** | 5 | `direct_mix`, `level`, `pattern` (0–19), `rate`, `trigger_sens` |
| **T Wah** | 7 | `direct_mix`, `frequency`, `level`, `mode`, `peak`, `polarity`, `sens` |
| **Tremolo** | 4 | `depth`, `level`, `rate`, `waveshape` |
| **Uni-V** | 3 | `depth`, `level`, `rate` |
| **Vibrato** | 3 | `depth`, `level`, `rate` |
| **Wave Synth** | 7 | `cutoff`, `decay`, `depth`, `level`, `resonance`, `sens`, `wave` |

**Design note:** never show all 84 at once. Pick the
effect, reveal its panel.

Pitch Shifter, Harmonist, Slow Gear, AC Processor, Parametric EQ and
Graphic EQ are selectable in a slot but their parameters are not mapped
yet — they use per-voice interval tables rather than plain knobs.

---

## Channel LEDs — read-only

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `led_boost` | enum | enum — 4 options | **read-only** |
| `led_delay` | enum | enum — 4 options | **read-only** |
| `led_fx` | enum | enum — 4 options | **read-only** |
| `led_mod` | enum | enum — 4 options | **read-only** |
| `led_reverb` | enum | enum — 4 options | **read-only** |

**Colours**: `0` off · `1` green · `2` red · `3` yellow

These report which colour channel each section is on. Writing them does
nothing on a MkII — render as indicators, never as inputs.

---

# Beyond parameters

## Channels — the most-used control

Eight stored sounds plus PANEL. This is what a player reaches for live, so
it deserves the most prominent place in the UI.

| Name | Program | |
|---|---|---|
| `a1` | PC 1 | BANK A |
| `a2` | PC 2 | BANK A |
| `a3` | PC 3 | BANK A |
| `a4` | PC 4 | BANK A |
| `panel` | PC 5 | live panel knobs |
| `b1` | PC 6 | BANK B |
| `b2` | PC 7 | BANK B |
| `b3` | PC 8 | BANK B |
| `b4` | PC 9 | BANK B |

Patch names are readable, so buttons can be labelled with the real sound
name rather than "CH1".

## Patch memory

Copy the live sound into one of the nine stored slots. **Destructive** —
it overwrites a saved channel permanently, so it wants a confirmation step.

## Tone Studio patches

`.tsl` files exported from BOSS Tone Studio can be listed, inspected and
loaded (109 parameters, about 2 seconds). A patch browser — file, patch
names, preview of the settings, load button — is a strong feature and the
data is already there.

## Effect switching by CC

The amp also accepts the footswitch messages, which is what a
foot-controller or a stomp-box row in the UI would send:

- CC 16 — boost
- CC 17 — mod
- CC 18 — fx
- CC 19 — delay
- CC 20 — reverb
- CC 21 — effect_loop

Expression: CC 80 (ga_fc_exp1), CC 81 (ga_fc_exp2), CC 82 (exp_pedal), CC 83 (ga_fc_fs1), CC 84 (ga_fc_fs2)

---

# Three constraints that shape the design

**1. Nothing reports a physical knob turn.** The amp never tells you when
someone touches it. Either the UI offers a refresh, or it polls, or it
accepts drifting out of date. Worth deciding before the layout is fixed,
because it determines whether the UI can present itself as authoritative.

**2. Effect parameters do not always read back.** A block only answers
when its effect is loaded in a slot. The UI needs a genuine "unknown"
state — not a zero, which would look like a real value.

**3. Two things are read-only.** `knob_volume` and the five LEDs report
state the amp will not let MIDI change. Render as indicators.

## Not reachable at all

Physical switches, per the official manual — no MIDI for any of them:
POWER CONTROL (0.5W / 50W / 100W), CAB RESONANCE, TAP tempo, bank A/B
hold-switch, STEREO EXPAND.
