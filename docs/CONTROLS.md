# Katana MkII — Control Reference

Every control this project can reach, for designing the web UI.
**553 parameters**, generated from `Param` (the same data
`GET /api/parameters` serves), so it cannot drift from the code.

The source for every address, range and label is Roland's own address map,
shipped inside BOSS Tone Studio. Ranges are in the units Tone Studio shows.

Each entry is one of three kinds, which is all the UI needs to render it:

| Kind | Widget |
|---|---|
| `range` | knob. Stepped ones carry `steps`: the text for each step ("1.25 kHz") |
| `toggle` | switch |
| `enum` | dropdown / segmented control |

---

## Amp

The main knob row, plus the amp-wide settings behind the **setup** button.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `amp_type` | enum | 33 choices |  |
| `gain` | range | 0 … 120 |  |
| `knob_volume` | range | 0 … 100 | **read-only** |
| `bass` | range | 0 … 100 |  |
| `middle` | range | 0 … 100 |  |
| `treble` | range | 0 … 100 |  |
| `presence` | range | 0 … 100 |  |
| `volume` | range | 0 … 100 |  |
| `bright` | toggle | off / on |  |
| `panel_amp_type` | enum | 5 choices | **read-only** |
| `variation` | toggle | off / on | **read-only** |
| `cabinet_resonance` | enum | 3 choices |  |
| `solo_switch` | toggle | off / on |  |
| `solo_level` | range | 0 … 100 |  |
| `contour_switch` | toggle | off / on |  |
| `contour_select` | enum | 3 choices |  |
| `contour1_type` | range | 0 … 3 |  |
| `contour1_freq_shift` | range | -50 … 50 | stored +50 |
| `contour2_type` | range | 0 … 3 |  |
| `contour2_freq_shift` | range | -50 … 50 | stored +50 |
| `contour3_type` | range | 0 … 3 |  |
| `contour3_freq_shift` | range | -50 … 50 | stored +50 |

**Amp models**: `0` Natural Clean · `1` Full Range · `2` Combo Crunch · `3` Stack Crunch · `4` HiGain Stack · `5` Power Drive · `6` Extreme Lead · `7` Core Metal · `8` JC-120 · `9` Clean Twin · `10` Pro Crunch · `11` Tweed · `12` Deluxe Crunch · `13` VO Drive · `14` VO Lead · `15` Match Drive · `16` BG Lead · `17` BG Drive · `18` MS1959 I · `19` MS1959 I+II · `20` R-Fire Vintage · `21` R-Fire Modern · `22` T-Amp Lead · `23` SLDN · `24` 5150 Drive · `25` Custom · `26` BGNR UB · `27` Orng RB · `28` MkII amp 28 · `29` MkII amp 29 · `30` MkII amp 30 · `31` MkII amp 31 · `32` MkII amp 32

Only five are reachable from the front panel; the rest are MIDI-only.
28–32 are MkII-only and named nowhere — not even in Tone Studio, which only
ever shows `panel_amp_type` + `variation` and lets the amp pick `amp_type`.
Reading `amp_type` after each TYPE/VARIATION combination would name them.

**Panel types** (`panel_amp_type`): `0` Acoustic · `1` Clean · `2` Crunch · `3` Lead · `4` Brown

**Cabinet resonance**: `0` Vintage · `1` Modern · `2` Deep — a patch
setting, despite the official manual listing it as a physical switch only.

---

## Boost / Overdrive

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `boost_switch` | toggle | off / on |  |
| `boost_type` | enum | 23 choices |  |
| `boost_drive` | range | 0 … 120 |  |
| `boost_bottom` | range | -50 … 50 | stored +50 |
| `boost_tone` | range | -50 … 50 | stored +50 |
| `boost_solo_switch` | toggle | off / on |  |
| `boost_solo_level` | range | 0 … 100 |  |
| `boost_level` | range | 0 … 100 |  |
| `boost_direct_mix` | range | 0 … 100 |  |

**Pedal models**: `0` Mid Boost · `1` Clean Boost · `2` Treble Boost · `3` Crunch OD · `4` Natural OD · `5` Warm OD · `6` Fat DS · `8` Metal DS · `9` Oct Fuzz · `10` Blues Drive · `11` Overdrive · `12` T-Scream · `13` Turbo OD · `14` Distortion · `15` Rat · `16` Guv DS · `17` DST+ · `18` Metal Zone · `19` '60s Fuzz · `20` Muff Fuzz · `21` HM-2 · `22` Metal Core · `23` Centa OD

---

## Delay

Two independent delay engines with identical controls. The second is the
same names prefixed `delay2_`, 0x20 further on. Some settings only matter
for one type: `tap_time` for Pan, `mod_*` for Modulate and SDE-3000,
`sde_*` for SDE-3000. The editor shows only the active type's.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `delay_switch` | toggle | off / on |  |
| `delay_type` | enum | 8 choices |  |
| `delay_time` | range | 1 … 2000 ms | 2 bytes |
| `delay_feedback` | range | 0 … 100 |  |
| `delay_high_cut` | range | 630 Hz … FLAT |  |
| `delay_level` | range | 0 … 120 |  |
| `delay_direct_mix` | range | 0 … 100 |  |
| `delay_tap_time` | range | 0 … 100 |  |
| `delay_mod_rate` | range | 0 … 100 |  |
| `delay_mod_depth` | range | 0 … 100 |  |
| `delay_sde_range` | enum | 2 choices |  |
| `delay_sde_filter` | toggle | off / on |  |
| `delay_sde_feedback_phase` | enum | 2 choices |  |
| `delay_sde_delay_phase` | enum | 2 choices |  |
| `delay_sde_mod_switch` | toggle | off / on |  |

**Delay types**: `0` Digital · `1` Pan · `2` Stereo · `6` Reverse · `7` Analog · `8` Tape Echo · `9` Modulate · `10` SDE-3000

---

## Reverb

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `reverb_switch` | toggle | off / on |  |
| `reverb_type` | enum | 5 choices |  |
| `reverb_time` | range | 1 … 100 | stored -1 |
| `reverb_pre_delay` | range | 0 … 500 ms | 2 bytes |
| `reverb_low_cut` | range | FLAT … 800 Hz |  |
| `reverb_high_cut` | range | 630 Hz … FLAT |  |
| `reverb_density` | range | 0 … 10 |  |
| `reverb_level` | range | 0 … 100 |  |
| `reverb_direct_mix` | range | 0 … 100 |  |
| `reverb_spring_color` | range | 0 … 100 |  |

**Reverb types**: `1` Room · `3` Hall · `4` Plate · `5` Spring · `6` Modulate

The amp accepts 0 and 2 as well, but Tone Studio never offers them. The
older names here (Reverb+Delay, Fast Decay) came from first-generation
Katana docs and were wrong for the MkII.

---

## Pedal FX / expression pedal

`pedal_type` picks one of three modes, and each keeps its own settings.
The treadle drives whichever mode's `position` is active.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `pedal_switch` | toggle | off / on |  |
| `pedal_type` | enum | 3 choices |  |
| `pedal_position` | enum | 2 choices |  |
| `wah_type` | enum | 6 choices |  |
| `wah_position` | range | 0 … 100 |  |
| `wah_pedal_min` | range | 0 … 100 |  |
| `wah_pedal_max` | range | 0 … 100 |  |
| `wah_level` | range | 0 … 100 |  |
| `wah_direct_mix` | range | 0 … 100 |  |
| `pedal_bend_pitch` | range | -24 … 24 | stored +24 |
| `pedal_bend_position` | range | 0 … 100 |  |
| `pedal_bend_level` | range | 0 … 100 |  |
| `pedal_bend_direct_mix` | range | 0 … 100 |  |
| `wah_95e_position` | range | 0 … 100 |  |
| `wah_95e_pedal_min` | range | 0 … 100 |  |
| `wah_95e_pedal_max` | range | 0 … 100 |  |
| `wah_95e_level` | range | 0 … 100 |  |
| `wah_95e_direct_mix` | range | 0 … 100 |  |
| `foot_volume` | range | 0 … 100 |  |

**Pedal modes**: `0` Wah · `1` Pedal Bend · `2` Wah 95E

**Wah voicings**: `0` Cry Wah · `1` Vo Wah · `2` Fat Wah · `3` Light Wah · `4` 7 String Wah · `5` Reso Wah

`wah_position` (and its two siblings) are the treadle. It is the one
control that exists to be *swept* rather than set — worth a large vertical
or rotary widget. A sweep must be driven server-side in one request, not
stepped from the browser.

---

## EQ

One block with two types: `eq_type` picks parametric or the GE-10 graphic
EQ. Each type keeps its own settings.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `eq_switch` | toggle | off / on |  |
| `eq_type` | enum | 2 choices |  |
| `eq_position` | enum | 2 choices |  |
| `eq_low_cut` | range | FLAT … 800 Hz |  |
| `eq_low_gain` | range | -20 … 20 dB | stored +20 |
| `eq_low_mid_freq` | range | 20.0 Hz … 10.0 kHz |  |
| `eq_low_mid_q` | range | 0.5 … 16 |  |
| `eq_low_mid_gain` | range | -20 … 20 dB | stored +20 |
| `eq_high_mid_freq` | range | 20.0 Hz … 10.0 kHz |  |
| `eq_high_mid_q` | range | 0.5 … 16 |  |
| `eq_high_mid_gain` | range | -20 … 20 dB | stored +20 |
| `eq_high_gain` | range | -20 … 20 dB | stored +20 |
| `eq_high_cut` | range | 630 Hz … FLAT |  |
| `eq_peq_level` | range | -20 … 20 dB | stored +20 |
| `eq_band_31hz` | range | -24 … 24 dB | stored +24 |
| `eq_band_62hz` | range | -24 … 24 dB | stored +24 |
| `eq_band_125hz` | range | -24 … 24 dB | stored +24 |
| `eq_band_250hz` | range | -24 … 24 dB | stored +24 |
| `eq_band_500hz` | range | -24 … 24 dB | stored +24 |
| `eq_band_1khz` | range | -24 … 24 dB | stored +24 |
| `eq_band_2khz` | range | -24 … 24 dB | stored +24 |
| `eq_band_4khz` | range | -24 … 24 dB | stored +24 |
| `eq_band_8khz` | range | -24 … 24 dB | stored +24 |
| `eq_band_16khz` | range | -24 … 24 dB | stored +24 |
| `eq_level` | range | -24 … 24 dB | stored +24 |

Band order for a fader row: 31Hz · 62 · 125 · 250 · 500 · 1k · 2k · 4k ·
8k · 16k.

This is where a tone lives. The Pantera patch, for reference, is
+14 / +14 / +12 / −6 / −12 / −15 / −7 / +8 / +10 / +11 — a deep mid scoop
with boosted extremes.

---

## Effects loop (SEND / RETURN)

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `send_return_switch` | toggle | off / on |  |
| `send_return_mode` | enum | 2 choices |  |
| `send_return_position` | enum | 2 choices |  |
| `send_return_send_level` | range | 0 … 100 |  |
| `send_return_return_level` | range | 0 … 100 |  |

The panel's LOOP footswitch (CC 21) toggles `send_return_switch`.

---

## Noise gate

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `noise_suppressor_switch` | toggle | off / on |  |
| `noise_suppressor_threshold` | range | 0 … 100 |  |
| `noise_suppressor_release` | range | 0 … 100 |  |

---

## Effect slots

Two slots: MOD (slot 1) and FX (slot 2), each loading one of
**31 effects**.

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `fx1_switch` | toggle | off / on |  |
| `fx1_type` | enum | 31 choices |  |
| `fx2_switch` | toggle | off / on |  |
| `fx2_type` | enum | 31 choices |  |
| `master_key` | enum | 12 choices |  |

`master_key` is the key the Harmonist harmonises in; both slots share it.

### Per-effect parameters

Behind those slots sit **420 parameters** — every effect's own
knobs, once per slot: `fx1_<effect>_<knob>` and `fx2_<effect>_<knob>`.
Each slot keeps settings for every effect at once, whatever it is set to,
so an effect can be dialled in before it is selected, and the two slots
never share a knob. The table lives in `katana_amp/effects.py`.

| Type | Effect | Key | Knobs |
|---|---|---|---|
| `0` | **T Wah** | `t_wah` | `mode` (LPF / BPF), `polarity` (Down / Up), `sens` (0 … 100), `frequency` (0 … 100), `peak` (0 … 100), `direct_mix` (0 … 100), `level` (0 … 100) |
| `1` | **Auto Wah** | `auto_wah` | `mode` (LPF / BPF), `frequency` (0 … 100), `peak` (0 … 100), `rate` (0 … 100), `depth` (0 … 100), `direct_mix` (0 … 100), `level` (0 … 100) |
| `2` | **Pedal Wah** | `pedal_wah` | `type` (Cry Wah / Vo Wah / Fat Wah / Light Wah / 7 String Wah / Reso Wah), `position` (0 … 100), `pedal_min` (0 … 100), `pedal_max` (0 … 100), `level` (0 … 100), `direct_mix` (0 … 100) |
| `3` | **Comp** | `comp` | `type` (Boss Comp / Hi-Band / Light / D-Comp / Orange / Fat / Mild), `sustain` (0 … 100), `attack` (0 … 100), `tone` (-50 … 50), `level` (0 … 100) |
| `4` | **Limiter** | `limiter` | `type` (Boss Limiter / Rack 160D / Vintage Rack U), `attack` (0 … 100), `threshold` (0 … 100), `ratio` (1:1 … INF:1), `release` (0 … 100), `level` (0 … 100) |
| `6` | **Graphic EQ** | `graphic_eq` | `band_31hz` (-20 … 20 dB), `band_62hz` (-20 … 20 dB), `band_125hz` (-20 … 20 dB), `band_250hz` (-20 … 20 dB), `band_500hz` (-20 … 20 dB), `band_1khz` (-20 … 20 dB), `band_2khz` (-20 … 20 dB), `band_4khz` (-20 … 20 dB), `band_8khz` (-20 … 20 dB), `band_16khz` (-20 … 20 dB), `level` (-20 … 20 dB) |
| `7` | **Parametric EQ** | `parametric_eq` | `low_cut` (FLAT … 800 Hz), `low_gain` (-20 … 20 dB), `low_mid_freq` (20.0 Hz … 10.0 kHz), `low_mid_q` (0.5 … 16), `low_mid_gain` (-20 … 20 dB), `high_mid_freq` (20.0 Hz … 10.0 kHz), `high_mid_q` (0.5 … 16), `high_mid_gain` (-20 … 20 dB), `high_gain` (-20 … 20 dB), `high_cut` (630 Hz … FLAT), `level` (-20 … 20 dB) |
| `9` | **Guitar Sim** | `guitar_sim` | `type` (S->H / H->S / H->HF / S->Hollow / H->Hollow / S->AC / H->AC / P->AC), `low` (-50 … 50), `high` (-50 … 50), `level` (0 … 100), `body` (0 … 100) |
| `10` | **Slow Gear** | `slow_gear` | `sens` (0 … 100), `rise_time` (0 … 100), `level` (0 … 100) |
| `12` | **Wave Synth** | `wave_synth` | `wave` (Saw / Square), `cutoff` (0 … 100), `resonance` (0 … 100), `sens` (0 … 100), `decay` (0 … 100), `depth` (0 … 100), `level` (0 … 100), `direct_mix` (0 … 100) |
| `14` | **Octave** | `octave` | `range` (Range 1 / Range 2 / Range 3 / Range 4), `level` (0 … 100), `direct_mix` (0 … 100) |
| `15` | **Pitch Shifter** | `pitch_shifter` | `voice` (1 Voice / 2 Voice), `mode1` (Fast / Medium / Slow / Mono), `pitch1` (-24 … 24), `fine1` (-50 … 50), `pre_delay1` (0 … 300 ms), `level1` (0 … 100), `mode2` (Fast / Medium / Slow / Mono), `pitch2` (-24 … 24), `fine2` (-50 … 50), `pre_delay2` (0 … 300 ms), `level2` (0 … 100), `feedback` (0 … 100), `direct_mix` (0 … 100) |
| `16` | **Harmonist** | `harmonist` | `voice` (1 Voice / 2 Voice), `harmony1` (-2oct … USER), `pre_delay1` (0 … 300 ms), `level1` (0 … 100), `harmony2` (-2oct … USER), `pre_delay2` (0 … 300 ms), `level2` (0 … 100), `feedback` (0 … 100), `direct_mix` (0 … 100), `user1_c` (-24 … 24), `user1_db` (-24 … 24), `user1_d` (-24 … 24), `user1_eb` (-24 … 24), `user1_e` (-24 … 24), `user1_f` (-24 … 24), `user1_fs` (-24 … 24), `user1_g` (-24 … 24), `user1_ab` (-24 … 24), `user1_a` (-24 … 24), `user1_bb` (-24 … 24), `user1_b` (-24 … 24), `user2_c` (-24 … 24), `user2_db` (-24 … 24), `user2_d` (-24 … 24), `user2_eb` (-24 … 24), `user2_e` (-24 … 24), `user2_f` (-24 … 24), `user2_fs` (-24 … 24), `user2_g` (-24 … 24), `user2_ab` (-24 … 24), `user2_a` (-24 … 24), `user2_bb` (-24 … 24), `user2_b` (-24 … 24) |
| `18` | **AC Processor** | `ac_processor` | `type` (Small / Medium / Bright / Power), `bass` (-50 … 50), `middle` (-50 … 50), `middle_freq` (20.0 Hz … 10.0 kHz), `treble` (-50 … 50), `presence` (-50 … 50), `level` (0 … 100) |
| `19` | **Phaser** | `phaser` | `type` (4 Stage / 8 Stage / 12 Stage / BiPhase), `rate` (0 … 100), `depth` (0 … 100), `manual` (0 … 100), `resonance` (0 … 100), `step_rate` (OFF … 100), `level` (0 … 100), `direct_mix` (0 … 100) |
| `20` | **Flanger** | `flanger` | `rate` (0 … 100), `depth` (0 … 100), `manual` (0 … 100), `resonance` (0 … 100), `low_cut` (FLAT … 800 Hz), `level` (0 … 100), `direct_mix` (0 … 100) |
| `21` | **Tremolo** | `tremolo` | `waveshape` (0 … 100), `rate` (0 … 100), `depth` (0 … 100), `level` (0 … 100) |
| `22` | **Rotary** | `rotary` | `rate_fast` (0 … 100), `depth` (0 … 100), `level` (0 … 100) |
| `23` | **Uni-V** | `uni_v` | `rate` (0 … 100), `depth` (0 … 100), `level` (0 … 100) |
| `25` | **Slicer** | `slicer` | `pattern` (P1 … P20), `rate` (0 … 100), `trigger_sens` (0 … 100), `level` (0 … 100), `direct_mix` (0 … 100) |
| `26` | **Vibrato** | `vibrato` | `rate` (0 … 100), `depth` (0 … 100), `level` (0 … 100) |
| `27` | **Ring Mod** | `ring_mod` | `mode` (Normal / Intelligent), `frequency` (0 … 100), `level` (0 … 100), `direct_mix` (0 … 100) |
| `28` | **Humanizer** | `humanizer` | `mode` (Picking / Auto), `vowel1` (A / E / I / O / U), `vowel2` (A / E / I / O / U), `sens` (0 … 100), `rate` (0 … 100), `depth` (0 … 100), `manual` (0 … 100), `level` (0 … 100) |
| `29` | **Chorus** | `chorus` | `crossover` (100 Hz … 4.00 kHz), `low_rate` (0 … 100), `low_depth` (0 … 100), `low_pre_delay` (0.0 ms … 40.0 ms), `low_level` (0 … 100), `high_rate` (0 … 100), `high_depth` (0 … 100), `high_pre_delay` (0.0 ms … 40.0 ms), `high_level` (0 … 100), `direct_mix` (0 … 100) |
| `31` | **AC Guitar Sim** | `ac_guitar_sim` | `high` (-50 … 50), `body` (0 … 100), `low` (-50 … 50), `level` (0 … 100) |
| `35` | **Phaser 90E** | `phaser_90e` | `script` (off / on), `speed` (0 … 100) |
| `36` | **Flanger 117E** | `flanger_117e` | `manual` (0 … 100), `width` (0 … 100), `speed` (0 … 100), `regen` (0 … 100) |
| `37` | **Wah 95E** | `wah_95e` | `position` (0 … 100), `pedal_min` (0 … 100), `pedal_max` (0 … 100), `level` (0 … 100), `direct_mix` (0 … 100) |
| `38` | **DC-30** | `dc_30` | `select` (Chorus / Echo), `input_volume` (0 … 100), `chorus_intensity` (0 … 100), `echo_repeat_rate` (40 … 600 ms), `echo_intensity` (0 … 100), `echo_volume` (0 … 100), `tone` (0 … 100), `output` (D+E / D/E) |
| `39` | **Heavy Octave** | `heavy_octave` | `oct1_level` (0 … 100), `oct2_level` (0 … 100), `direct_mix` (0 … 100) |
| `40` | **Pedal Bend** | `pedal_bend` | `pitch` (-24 … 24), `position` (0 … 100), `level` (0 … 100), `direct_mix` (0 … 100) |

Types 5, 8, 11, 13, 17, 24, 30 and 32–34 are accepted by the amp but no
effect uses them. The `/api/parameters` entry for each knob carries
`slot`, `effect` (the TYPE value) and `label`, so the UI builds a slot's
panel from the schema alone.

**Design note:** never show all of them at once. Pick the effect, reveal
its panel. The Harmonist's 24 per-note `user` intervals only matter when a
voice's harmony is set to USER.

---

## Channel LEDs — read-only

| Parameter | Type | Range | Notes |
|---|---|---|---|
| `led_boost` | enum | 4 choices | **read-only** |
| `led_mod` | enum | 4 choices | **read-only** |
| `led_fx` | enum | 4 choices | **read-only** |
| `led_delay` | enum | 4 choices | **read-only** |
| `led_reverb` | enum | 4 choices | **read-only** |

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
Every block of the patch is copied (Roland's block list, in
`katana.PATCH_BLOCKS`), and everything is read before anything is written.

## Tone Studio patches

`.tsl` files exported from BOSS Tone Studio can be listed, inspected and
loaded. A patch browser — file, patch names, preview of the settings, load
button — is a strong feature and the data is already there.

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

**2. A read can fail.** The amp occasionally drops a reply, and the
refresh skips a block that does not answer rather than retrying it. The UI
needs a genuine "unknown" state — not a zero, which would look like a real
value. (Tone Studio reads whole blocks, up to 128 bytes at a time, so the
refresh asks for no more than that per request.)

**3. Some things are read-only.** `knob_volume`, `panel_amp_type`,
`variation` and the five LEDs report state the amp will not let MIDI
change. Render as indicators.

## Not reachable at all

Physical switches, per the official manual — no MIDI for any of them:
POWER CONTROL (0.5W / 50W / 100W) and the bank A/B hold-switch.

In Roland's map but not in `Param` yet: the system area from `0x00000000`
(global EQ, STEREO EXPAND, line-out Air Feel, USB levels), the second EQ
(`Eq(2)`), solo EQ / solo delay, the per-colour effect assignments, knob
and pedal assignments, and the panel button commands at `0x7F0101xx`
(including delay TAP).
