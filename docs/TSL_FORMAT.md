# BOSS Tone Studio `.tsl` File Format

Reverse-engineered from KATANA MkII files and verified byte-for-byte
against a real amp. For building a `.tsl` viewer.

## Top level

A `.tsl` file is plain **JSON**:

```json
{
  "name": "DIME'D",
  "formatRev": "0002",
  "device": "KATANA MkII",
  "data": [ [ patch, patch, ... ] ]
}
```

| Field | Meaning |
|---|---|
| `name` | Name of the bank/file, set by whoever exported it |
| `formatRev` | Format revision — `"0002"` on MkII files |
| `device` | Must contain `KATANA` — reject anything else |
| `data` | **List of lists.** Flatten one level; each inner item is a patch |

A file can hold **one or many patches** (your Pantera file has 1, the
Trendkill file 2, the Children of Bodom file 5).

## A patch

```json
{
  "memo": "",
  "paramSet": {
    "UserPatch%PatchName": ["44", "49", "4D", ...],
    "UserPatch%Patch_0":   ["00", "0C", ...],
    ...
  }
}
```

- `memo` — free-text note, usually empty
- `paramSet` — **31 named blocks**, each a list of **hex strings** (`"1F"`),
  not numbers. Parse with `parseInt(x, 16)`.

Every block is a run of bytes copied straight out of the amp's memory.

## The blocks

| Block | Bytes | What it holds |
|---|---|---|
| `UserPatch%PatchName` | 16 | Patch name, ASCII, space-padded |
| `UserPatch%Patch_0` | 72 | **Boost, amp, and the graphic EQ** |
| `UserPatch%Fx(1)` | 225 | Effect slot 1 — all effect types' settings |
| `UserPatch%Fx(2)` | 225 | Effect slot 2 — same layout |
| `UserPatch%Delay(1)` | 26 | Delay engine 1 |
| `UserPatch%Delay(2)` | 26 | Delay engine 2 |
| `UserPatch%Patch_1` | 91 | **Reverb, wah/pedal, noise gate** |
| `UserPatch%Patch_2` | 36 | Effect chain order / routing |
| `UserPatch%Status` | 18 | Knob positions and channel LED state |
| `UserPatch%KnobAsgn` | 34 | Panel knob assignments |
| `UserPatch%ExpPedalAsgn` | 34 | Expression pedal assignment |
| `UserPatch%ExpPedalAsgnMinMax` | 78 | Its travel limits |
| `UserPatch%GafcExp1–3Asgn` | 34 each | GA-FC foot controller pedals |
| `UserPatch%GafcExp1–3AsgnMinMax` | 78 each | Their limits |
| `UserPatch%GafcExExp1–3Asgn` | 34 each | GA-FC expansion pedals |
| `UserPatch%GafcExExp1–3AsgnMinMax` | 78 each | Their limits |
| `UserPatch%FsAsgn` | 2 | Footswitch assignment |
| `UserPatch%CtrlAsgn` | 8 | Control assignments |
| `UserPatch%Patch_Mk2V2` | 22 | MkII-specific additions |
| `UserPatch%Contour(1–3)` | 2 each | Contour settings |
| `UserPatch%Eq(2)` | 24 | A second EQ (MkII v2 firmware), same layout as the one in `Patch_0` |

**Note on `Eq(2)`:** it has the same layout as bytes 48–71 of `Patch_0`,
but it is a separate, second EQ with its own switch, not a copy. Its
position in the chain is byte 89 of `Patch_1`. In `Param` as `eq2_*`.

---

# Decoding each block

Source: Roland's address map, shipped inside BOSS Tone Studio. The tables
below are generated from this project's `Param`, so they match the code.
"Stored" is the raw byte range in the file; the real value is
`stored - offset` where a note says so (an EQ band stored 0–48 is −24…+24 dB).

**Byte position is not address offset.** A block is a plain run of bytes,
but the amp's addresses skip from `xx7F` to the next `xx00`, because every
address byte only counts to 127. So byte 128 of `Fx(1)` lives at
`0x60000200`, not `0x60000180`. Converting: `address = base + (n // 128) * 0x100 + n % 128`
(`katana.advance()` does this). Forgetting it is why effect settings past
the first 128 bytes of a block used to go missing.

## `UserPatch%PatchName` — 16 bytes

ASCII, space-padded. `"folow the reaper"`, `"DIME'D"`, `"Southern Solo"`.

```js
name = bytes.map(b => String.fromCharCode(b)).join("").trim()
```

## `UserPatch%Patch_0` — 72 bytes

Boost, amp and the EQ (parametric and GE-10). Base `0x60000010`.

| Byte | Parameter | Stored | Notes |
|---|---|---|---|
| 0 | `boost_switch` | 0–1 |  |
| 1 | `boost_type` | 0–25 |  |
| 2 | `boost_drive` | 0–120 |  |
| 3 | `boost_bottom` | 0–100 | stored +50 |
| 4 | `boost_tone` | 0–100 | stored +50 |
| 5 | `boost_solo_switch` | 0–1 |  |
| 6 | `boost_solo_level` | 0–100 |  |
| 7 | `boost_level` | 0–100 |  |
| 8 | `boost_direct_mix` | 0–100 |  |
| 17 | `amp_type` | 0–32 |  |
| 18 | `gain` | 0–120 |  |
| 19 | `knob_volume` | 0–100 | **read-only** |
| 20 | `bass` | 0–100 |  |
| 21 | `middle` | 0–100 |  |
| 22 | `treble` | 0–100 |  |
| 23 | `presence` | 0–100 |  |
| 24 | `volume` | 0–100 |  |
| 25 | `bright` | 0–1 |  |
| 48 | `eq_switch` | 0–1 |  |
| 49 | `eq_type` | 0–1 |  |
| 50 | `eq_low_cut` | 0–17 |  |
| 51 | `eq_low_gain` | 0–40 | stored +20 |
| 52 | `eq_low_mid_freq` | 0–27 |  |
| 53 | `eq_low_mid_q` | 0–5 |  |
| 54 | `eq_low_mid_gain` | 0–40 | stored +20 |
| 55 | `eq_high_mid_freq` | 0–27 |  |
| 56 | `eq_high_mid_q` | 0–5 |  |
| 57 | `eq_high_mid_gain` | 0–40 | stored +20 |
| 58 | `eq_high_gain` | 0–40 | stored +20 |
| 59 | `eq_high_cut` | 0–14 |  |
| 60 | `eq_peq_level` | 0–40 | stored +20 |
| 61 | `eq_band_31hz` | 0–48 | stored +24 |
| 62 | `eq_band_62hz` | 0–48 | stored +24 |
| 63 | `eq_band_125hz` | 0–48 | stored +24 |
| 64 | `eq_band_250hz` | 0–48 | stored +24 |
| 65 | `eq_band_500hz` | 0–48 | stored +24 |
| 66 | `eq_band_1khz` | 0–48 | stored +24 |
| 67 | `eq_band_2khz` | 0–48 | stored +24 |
| 68 | `eq_band_4khz` | 0–48 | stored +24 |
| 69 | `eq_band_8khz` | 0–48 | stored +24 |
| 70 | `eq_band_16khz` | 0–48 | stored +24 |
| 71 | `eq_level` | 0–48 | stored +24 |

**Boost pedal models**: `0` Mid Boost · `1` Clean Boost · `2` Treble Boost · `3` Crunch OD · `4` Natural OD · `5` Warm OD · `6` Fat DS · `8` Metal DS · `9` Oct Fuzz · `10` Blues Drive · `11` Overdrive · `12` T-Scream · `13` Turbo OD · `14` Distortion · `15` Rat · `16` Guv DS · `17` DST+ · `18` Metal Zone · `19` '60s Fuzz · `20` Muff Fuzz · `21` HM-2 · `22` Metal Core · `23` Centa OD

**Amp models**: `0` Natural Clean · `1` Full Range · `2` Combo Crunch · `3` Stack Crunch · `4` HiGain Stack · `5` Power Drive · `6` Extreme Lead · `7` Core Metal · `8` JC-120 · `9` Clean Twin · `10` Pro Crunch · `11` Tweed · `12` Deluxe Crunch · `13` VO Drive · `14` VO Lead · `15` Match Drive · `16` BG Lead · `17` BG Drive · `18` MS1959 I · `19` MS1959 I+II · `20` R-Fire Vintage · `21` R-Fire Modern · `22` T-Amp Lead · `23` SLDN · `24` 5150 Drive · `25` Custom · `26` BGNR UB · `27` Orng RB · `28` MkII amp 28 · `29` MkII amp 29 · `30` MkII amp 30 · `31` MkII amp 31 · `32` MkII amp 32

**`knob_volume` (byte 19)** is the physical volume knob. The amp reports it
but ignores writes — display only.

## `UserPatch%Fx(1)` and `Fx(2)` — 225 bytes each

Base `0x60000100` (slot 1, MOD) and `0x60000300` (slot 2, FX). Same layout;
the table shows slot 1's names — slot 2's are the same with `fx2_`.

The block holds settings for **every effect type at once**, not just the
selected one — so a viewer can show what a patch has dialled in for an
effect even when that effect is not currently active.

| Byte | Parameter | Stored | Notes |
|---|---|---|---|
| 0 | `fx1_switch` | 0–1 |  |
| 1 | `fx1_type` | 0–40 |  |
| 2 | `fx1_t_wah_mode` | 0–1 |  |
| 3 | `fx1_t_wah_polarity` | 0–1 |  |
| 4 | `fx1_t_wah_sens` | 0–100 |  |
| 5 | `fx1_t_wah_frequency` | 0–100 |  |
| 6 | `fx1_t_wah_peak` | 0–100 |  |
| 7 | `fx1_t_wah_direct_mix` | 0–100 |  |
| 8 | `fx1_t_wah_level` | 0–100 |  |
| 9 | `fx1_auto_wah_mode` | 0–1 |  |
| 10 | `fx1_auto_wah_frequency` | 0–100 |  |
| 11 | `fx1_auto_wah_peak` | 0–100 |  |
| 12 | `fx1_auto_wah_rate` | 0–100 |  |
| 13 | `fx1_auto_wah_depth` | 0–100 |  |
| 14 | `fx1_auto_wah_direct_mix` | 0–100 |  |
| 15 | `fx1_auto_wah_level` | 0–100 |  |
| 16 | `fx1_pedal_wah_type` | 0–5 |  |
| 17 | `fx1_pedal_wah_position` | 0–100 |  |
| 18 | `fx1_pedal_wah_pedal_min` | 0–100 |  |
| 19 | `fx1_pedal_wah_pedal_max` | 0–100 |  |
| 20 | `fx1_pedal_wah_level` | 0–100 |  |
| 21 | `fx1_pedal_wah_direct_mix` | 0–100 |  |
| 22 | `fx1_comp_type` | 0–6 |  |
| 23 | `fx1_comp_sustain` | 0–100 |  |
| 24 | `fx1_comp_attack` | 0–100 |  |
| 25 | `fx1_comp_tone` | 0–100 | stored +50 |
| 26 | `fx1_comp_level` | 0–100 |  |
| 27 | `fx1_limiter_type` | 0–2 |  |
| 28 | `fx1_limiter_attack` | 0–100 |  |
| 29 | `fx1_limiter_threshold` | 0–100 |  |
| 30 | `fx1_limiter_ratio` | 0–17 |  |
| 31 | `fx1_limiter_release` | 0–100 |  |
| 32 | `fx1_limiter_level` | 0–100 |  |
| 33 | `fx1_graphic_eq_band_31hz` | 0–40 | stored +20 |
| 34 | `fx1_graphic_eq_band_62hz` | 0–40 | stored +20 |
| 35 | `fx1_graphic_eq_band_125hz` | 0–40 | stored +20 |
| 36 | `fx1_graphic_eq_band_250hz` | 0–40 | stored +20 |
| 37 | `fx1_graphic_eq_band_500hz` | 0–40 | stored +20 |
| 38 | `fx1_graphic_eq_band_1khz` | 0–40 | stored +20 |
| 39 | `fx1_graphic_eq_band_2khz` | 0–40 | stored +20 |
| 40 | `fx1_graphic_eq_band_4khz` | 0–40 | stored +20 |
| 41 | `fx1_graphic_eq_band_8khz` | 0–40 | stored +20 |
| 42 | `fx1_graphic_eq_band_16khz` | 0–40 | stored +20 |
| 43 | `fx1_graphic_eq_level` | 0–40 | stored +20 |
| 44 | `fx1_parametric_eq_low_cut` | 0–17 |  |
| 45 | `fx1_parametric_eq_low_gain` | 0–40 | stored +20 |
| 46 | `fx1_parametric_eq_low_mid_freq` | 0–27 |  |
| 47 | `fx1_parametric_eq_low_mid_q` | 0–5 |  |
| 48 | `fx1_parametric_eq_low_mid_gain` | 0–40 | stored +20 |
| 49 | `fx1_parametric_eq_high_mid_freq` | 0–27 |  |
| 50 | `fx1_parametric_eq_high_mid_q` | 0–5 |  |
| 51 | `fx1_parametric_eq_high_mid_gain` | 0–40 | stored +20 |
| 52 | `fx1_parametric_eq_high_gain` | 0–40 | stored +20 |
| 53 | `fx1_parametric_eq_high_cut` | 0–14 |  |
| 54 | `fx1_parametric_eq_level` | 0–40 | stored +20 |
| 55 | `fx1_guitar_sim_type` | 0–7 |  |
| 56 | `fx1_guitar_sim_low` | 0–100 | stored +50 |
| 57 | `fx1_guitar_sim_high` | 0–100 | stored +50 |
| 58 | `fx1_guitar_sim_level` | 0–100 |  |
| 59 | `fx1_guitar_sim_body` | 0–100 |  |
| 60 | `fx1_slow_gear_sens` | 0–100 |  |
| 61 | `fx1_slow_gear_rise_time` | 0–100 |  |
| 62 | `fx1_slow_gear_level` | 0–100 |  |
| 63 | `fx1_wave_synth_wave` | 0–1 |  |
| 64 | `fx1_wave_synth_cutoff` | 0–100 |  |
| 65 | `fx1_wave_synth_resonance` | 0–100 |  |
| 66 | `fx1_wave_synth_sens` | 0–100 |  |
| 67 | `fx1_wave_synth_decay` | 0–100 |  |
| 68 | `fx1_wave_synth_depth` | 0–100 |  |
| 69 | `fx1_wave_synth_level` | 0–100 |  |
| 70 | `fx1_wave_synth_direct_mix` | 0–100 |  |
| 71 | `fx1_octave_range` | 0–3 |  |
| 72 | `fx1_octave_level` | 0–100 |  |
| 73 | `fx1_octave_direct_mix` | 0–100 |  |
| 74 | `fx1_pitch_shifter_voice` | 0–1 |  |
| 75 | `fx1_pitch_shifter_mode1` | 0–3 |  |
| 76 | `fx1_pitch_shifter_pitch1` | 0–48 | stored +24 |
| 77 | `fx1_pitch_shifter_fine1` | 0–100 | stored +50 |
| 78 | `fx1_pitch_shifter_pre_delay1` | 0–300 | 2 bytes |
| 80 | `fx1_pitch_shifter_level1` | 0–100 |  |
| 81 | `fx1_pitch_shifter_mode2` | 0–3 |  |
| 82 | `fx1_pitch_shifter_pitch2` | 0–48 | stored +24 |
| 83 | `fx1_pitch_shifter_fine2` | 0–100 | stored +50 |
| 84 | `fx1_pitch_shifter_pre_delay2` | 0–300 | 2 bytes |
| 86 | `fx1_pitch_shifter_level2` | 0–100 |  |
| 87 | `fx1_pitch_shifter_feedback` | 0–100 |  |
| 88 | `fx1_pitch_shifter_direct_mix` | 0–100 |  |
| 89 | `fx1_harmonist_voice` | 0–1 |  |
| 90 | `fx1_harmonist_harmony1` | 0–29 |  |
| 91 | `fx1_harmonist_pre_delay1` | 0–300 | 2 bytes |
| 93 | `fx1_harmonist_level1` | 0–100 |  |
| 94 | `fx1_harmonist_harmony2` | 0–29 |  |
| 95 | `fx1_harmonist_pre_delay2` | 0–300 | 2 bytes |
| 97 | `fx1_harmonist_level2` | 0–100 |  |
| 98 | `fx1_harmonist_feedback` | 0–100 |  |
| 99 | `fx1_harmonist_direct_mix` | 0–100 |  |
| 100 | `fx1_harmonist_user1_c` | 0–48 | stored +24 |
| 101 | `fx1_harmonist_user1_db` | 0–48 | stored +24 |
| 102 | `fx1_harmonist_user1_d` | 0–48 | stored +24 |
| 103 | `fx1_harmonist_user1_eb` | 0–48 | stored +24 |
| 104 | `fx1_harmonist_user1_e` | 0–48 | stored +24 |
| 105 | `fx1_harmonist_user1_f` | 0–48 | stored +24 |
| 106 | `fx1_harmonist_user1_fs` | 0–48 | stored +24 |
| 107 | `fx1_harmonist_user1_g` | 0–48 | stored +24 |
| 108 | `fx1_harmonist_user1_ab` | 0–48 | stored +24 |
| 109 | `fx1_harmonist_user1_a` | 0–48 | stored +24 |
| 110 | `fx1_harmonist_user1_bb` | 0–48 | stored +24 |
| 111 | `fx1_harmonist_user1_b` | 0–48 | stored +24 |
| 112 | `fx1_harmonist_user2_c` | 0–48 | stored +24 |
| 113 | `fx1_harmonist_user2_db` | 0–48 | stored +24 |
| 114 | `fx1_harmonist_user2_d` | 0–48 | stored +24 |
| 115 | `fx1_harmonist_user2_eb` | 0–48 | stored +24 |
| 116 | `fx1_harmonist_user2_e` | 0–48 | stored +24 |
| 117 | `fx1_harmonist_user2_f` | 0–48 | stored +24 |
| 118 | `fx1_harmonist_user2_fs` | 0–48 | stored +24 |
| 119 | `fx1_harmonist_user2_g` | 0–48 | stored +24 |
| 120 | `fx1_harmonist_user2_ab` | 0–48 | stored +24 |
| 121 | `fx1_harmonist_user2_a` | 0–48 | stored +24 |
| 122 | `fx1_harmonist_user2_bb` | 0–48 | stored +24 |
| 123 | `fx1_harmonist_user2_b` | 0–48 | stored +24 |
| 124 | `fx1_ac_processor_type` | 0–3 |  |
| 125 | `fx1_ac_processor_bass` | 0–100 | stored +50 |
| 126 | `fx1_ac_processor_middle` | 0–100 | stored +50 |
| 127 | `fx1_ac_processor_middle_freq` | 0–27 |  |
| 128 | `fx1_ac_processor_treble` | 0–100 | stored +50 |
| 129 | `fx1_ac_processor_presence` | 0–100 | stored +50 |
| 130 | `fx1_ac_processor_level` | 0–100 |  |
| 131 | `fx1_phaser_type` | 0–3 |  |
| 132 | `fx1_phaser_rate` | 0–100 |  |
| 133 | `fx1_phaser_depth` | 0–100 |  |
| 134 | `fx1_phaser_manual` | 0–100 |  |
| 135 | `fx1_phaser_resonance` | 0–100 |  |
| 136 | `fx1_phaser_step_rate` | 0–101 | stored +1 |
| 137 | `fx1_phaser_level` | 0–100 |  |
| 138 | `fx1_phaser_direct_mix` | 0–100 |  |
| 139 | `fx1_flanger_rate` | 0–100 |  |
| 140 | `fx1_flanger_depth` | 0–100 |  |
| 141 | `fx1_flanger_manual` | 0–100 |  |
| 142 | `fx1_flanger_resonance` | 0–100 |  |
| 144 | `fx1_flanger_low_cut` | 0–10 |  |
| 145 | `fx1_flanger_level` | 0–100 |  |
| 146 | `fx1_flanger_direct_mix` | 0–100 |  |
| 147 | `fx1_tremolo_waveshape` | 0–100 |  |
| 148 | `fx1_tremolo_rate` | 0–100 |  |
| 149 | `fx1_tremolo_depth` | 0–100 |  |
| 150 | `fx1_tremolo_level` | 0–100 |  |
| 153 | `fx1_rotary_rate_fast` | 0–100 |  |
| 156 | `fx1_rotary_depth` | 0–100 |  |
| 157 | `fx1_rotary_level` | 0–100 |  |
| 158 | `fx1_uni_v_rate` | 0–100 |  |
| 159 | `fx1_uni_v_depth` | 0–100 |  |
| 160 | `fx1_uni_v_level` | 0–100 |  |
| 161 | `fx1_slicer_pattern` | 0–19 |  |
| 162 | `fx1_slicer_rate` | 0–100 |  |
| 163 | `fx1_slicer_trigger_sens` | 0–100 |  |
| 164 | `fx1_slicer_level` | 0–100 |  |
| 165 | `fx1_slicer_direct_mix` | 0–100 |  |
| 166 | `fx1_vibrato_rate` | 0–100 |  |
| 167 | `fx1_vibrato_depth` | 0–100 |  |
| 170 | `fx1_vibrato_level` | 0–100 |  |
| 171 | `fx1_ring_mod_mode` | 0–1 |  |
| 172 | `fx1_ring_mod_frequency` | 0–100 |  |
| 173 | `fx1_ring_mod_level` | 0–100 |  |
| 174 | `fx1_ring_mod_direct_mix` | 0–100 |  |
| 175 | `fx1_humanizer_mode` | 0–1 |  |
| 176 | `fx1_humanizer_vowel1` | 0–4 |  |
| 177 | `fx1_humanizer_vowel2` | 0–4 |  |
| 178 | `fx1_humanizer_sens` | 0–100 |  |
| 179 | `fx1_humanizer_rate` | 0–100 |  |
| 180 | `fx1_humanizer_depth` | 0–100 |  |
| 181 | `fx1_humanizer_manual` | 0–100 |  |
| 182 | `fx1_humanizer_level` | 0–100 |  |
| 183 | `fx1_chorus_crossover` | 0–16 |  |
| 184 | `fx1_chorus_low_rate` | 0–100 |  |
| 185 | `fx1_chorus_low_depth` | 0–100 |  |
| 186 | `fx1_chorus_low_pre_delay` | 0–80 |  |
| 187 | `fx1_chorus_low_level` | 0–100 |  |
| 188 | `fx1_chorus_high_rate` | 0–100 |  |
| 189 | `fx1_chorus_high_depth` | 0–100 |  |
| 190 | `fx1_chorus_high_pre_delay` | 0–80 |  |
| 191 | `fx1_chorus_high_level` | 0–100 |  |
| 192 | `fx1_chorus_direct_mix` | 0–100 |  |
| 193 | `fx1_ac_guitar_sim_high` | 0–100 | stored +50 |
| 194 | `fx1_ac_guitar_sim_body` | 0–100 |  |
| 195 | `fx1_ac_guitar_sim_low` | 0–100 | stored +50 |
| 197 | `fx1_ac_guitar_sim_level` | 0–100 |  |
| 198 | `fx1_phaser_90e_script` | 0–1 |  |
| 199 | `fx1_phaser_90e_speed` | 0–100 |  |
| 200 | `fx1_flanger_117e_manual` | 0–100 |  |
| 201 | `fx1_flanger_117e_width` | 0–100 |  |
| 202 | `fx1_flanger_117e_speed` | 0–100 |  |
| 203 | `fx1_flanger_117e_regen` | 0–100 |  |
| 204 | `fx1_wah_95e_position` | 0–100 |  |
| 205 | `fx1_wah_95e_pedal_min` | 0–100 |  |
| 206 | `fx1_wah_95e_pedal_max` | 0–100 |  |
| 207 | `fx1_wah_95e_level` | 0–100 |  |
| 208 | `fx1_wah_95e_direct_mix` | 0–100 |  |
| 209 | `fx1_dc_30_select` | 0–1 |  |
| 210 | `fx1_dc_30_input_volume` | 0–100 |  |
| 211 | `fx1_dc_30_chorus_intensity` | 0–100 |  |
| 212 | `fx1_dc_30_echo_repeat_rate` | 40–600 | 2 bytes |
| 214 | `fx1_dc_30_echo_intensity` | 0–100 |  |
| 215 | `fx1_dc_30_echo_volume` | 0–100 |  |
| 216 | `fx1_dc_30_tone` | 0–100 |  |
| 217 | `fx1_dc_30_output` | 0–1 |  |
| 218 | `fx1_heavy_octave_oct1_level` | 0–100 |  |
| 219 | `fx1_heavy_octave_oct2_level` | 0–100 |  |
| 220 | `fx1_heavy_octave_direct_mix` | 0–100 |  |
| 221 | `fx1_pedal_bend_pitch` | 0–48 | stored +24 |
| 222 | `fx1_pedal_bend_position` | 0–100 |  |
| 223 | `fx1_pedal_bend_level` | 0–100 |  |
| 224 | `fx1_pedal_bend_direct_mix` | 0–100 |  |

**Effect types** (byte 1): `0` T Wah · `1` Auto Wah · `2` Pedal Wah · `3` Comp · `4` Limiter · `6` Graphic EQ · `7` Parametric EQ · `9` Guitar Sim · `10` Slow Gear · `12` Wave Synth · `14` Octave · `15` Pitch Shifter · `16` Harmonist · `18` AC Processor · `19` Phaser · `20` Flanger · `21` Tremolo · `22` Rotary · `23` Uni-V · `25` Slicer · `26` Vibrato · `27` Ring Mod · `28` Humanizer · `29` Chorus · `31` AC Guitar Sim · `35` Phaser 90E · `36` Flanger 117E · `37` Wah 95E · `38` DC-30 · `39` Heavy Octave · `40` Pedal Bend

Gaps in the byte numbers are bytes Roland's map lists without a name.

## `UserPatch%Delay(1)` / `Delay(2)` — 26 bytes each

Base `0x60000500` and `0x60000520`.

| Byte | Parameter | Stored | Notes |
|---|---|---|---|
| 0 | `delay_switch` | 0–1 |  |
| 1 | `delay_type` | 0–10 |  |
| 2 | `delay_time` | 1–2000 | 2 bytes |
| 4 | `delay_feedback` | 0–100 |  |
| 5 | `delay_high_cut` | 0–14 |  |
| 6 | `delay_level` | 0–120 |  |
| 7 | `delay_direct_mix` | 0–100 |  |
| 8 | `delay_tap_time` | 0–100 |  |
| 19 | `delay_mod_rate` | 0–100 |  |
| 20 | `delay_mod_depth` | 0–100 |  |
| 21 | `delay_sde_range` | 0–1 |  |
| 22 | `delay_sde_filter` | 0–1 |  |
| 23 | `delay_sde_feedback_phase` | 0–1 |  |
| 24 | `delay_sde_delay_phase` | 0–1 |  |
| 25 | `delay_sde_mod_switch` | 0–1 |  |

**Delay types**: `0` Digital · `1` Pan · `2` Stereo · `6` Reverse · `7` Analog · `8` Tape Echo · `9` Modulate · `10` SDE-3000

## `UserPatch%Patch_1` — 91 bytes

Reverb, pedal FX, foot volume, the effects loop, the noise gate, the
Harmonist key, solo and contour. Base `0x60000540`; bytes 64 and up sit at
`0x60000600` and up.

| Byte | Parameter | Stored | Notes |
|---|---|---|---|
| 0 | `reverb_switch` | 0–1 |  |
| 1 | `reverb_type` | 0–6 |  |
| 2 | `reverb_time` | 0–99 | stored -1 |
| 3 | `reverb_pre_delay` | 0–500 | 2 bytes |
| 5 | `reverb_low_cut` | 0–17 |  |
| 6 | `reverb_high_cut` | 0–14 |  |
| 7 | `reverb_density` | 0–10 |  |
| 8 | `reverb_level` | 0–100 |  |
| 9 | `reverb_direct_mix` | 0–100 |  |
| 11 | `reverb_spring_color` | 0–100 |  |
| 16 | `pedal_switch` | 0–1 |  |
| 17 | `pedal_type` | 0–2 |  |
| 18 | `wah_type` | 0–5 |  |
| 19 | `wah_position` | 0–100 |  |
| 20 | `wah_pedal_min` | 0–100 |  |
| 21 | `wah_pedal_max` | 0–100 |  |
| 22 | `wah_level` | 0–100 |  |
| 23 | `wah_direct_mix` | 0–100 |  |
| 24 | `pedal_bend_pitch` | 0–48 | stored +24 |
| 25 | `pedal_bend_position` | 0–100 |  |
| 26 | `pedal_bend_level` | 0–100 |  |
| 27 | `pedal_bend_direct_mix` | 0–100 |  |
| 28 | `wah_95e_position` | 0–100 |  |
| 29 | `wah_95e_pedal_min` | 0–100 |  |
| 30 | `wah_95e_pedal_max` | 0–100 |  |
| 31 | `wah_95e_level` | 0–100 |  |
| 32 | `wah_95e_direct_mix` | 0–100 |  |
| 33 | `foot_volume` | 0–100 |  |
| 34 | `send_return_switch` | 0–1 |  |
| 35 | `send_return_mode` | 0–1 |  |
| 36 | `send_return_send_level` | 0–100 |  |
| 37 | `send_return_return_level` | 0–100 |  |
| 38 | `noise_suppressor_switch` | 0–1 |  |
| 39 | `noise_suppressor_threshold` | 0–100 |  |
| 40 | `noise_suppressor_release` | 0–100 |  |
| 49 | `master_key` | 0–11 |  |
| 84 | `solo_switch` | 0–1 |  |
| 85 | `solo_level` | 0–100 |  |
| 86 | `contour_switch` | 0–1 |  |
| 87 | `contour_select` | 0–2 |  |
| 89 | `eq2_position` | 0–1 |  |

**Reverb types**: `1` Room · `3` Hall · `4` Plate · `5` Spring · `6` Modulate. The amp accepts 0 and
2 as well, but Tone Studio never offers them.
**Pedal modes**: `0` Wah · `1` Pedal Bend · `2` Wah 95E
**Wah voicings**: `0` Cry Wah · `1` Vo Wah · `2` Fat Wah · `3` Light Wah · `4` 7 String Wah · `5` Reso Wah

## `UserPatch%Eq(2)` — 24 bytes

Base `0x60000060`. The second EQ: the same layout as bytes 48–71 of
`Patch_0`, with its own switch.

| Byte | Parameter | Stored | Notes |
|---|---|---|---|
| 0 | `eq2_switch` | 0–1 |  |
| 1 | `eq2_type` | 0–1 |  |
| 2 | `eq2_low_cut` | 0–17 |  |
| 3 | `eq2_low_gain` | 0–40 | stored +20 |
| 4 | `eq2_low_mid_freq` | 0–27 |  |
| 5 | `eq2_low_mid_q` | 0–5 |  |
| 6 | `eq2_low_mid_gain` | 0–40 | stored +20 |
| 7 | `eq2_high_mid_freq` | 0–27 |  |
| 8 | `eq2_high_mid_q` | 0–5 |  |
| 9 | `eq2_high_mid_gain` | 0–40 | stored +20 |
| 10 | `eq2_high_gain` | 0–40 | stored +20 |
| 11 | `eq2_high_cut` | 0–14 |  |
| 12 | `eq2_peq_level` | 0–40 | stored +20 |
| 13 | `eq2_band_31hz` | 0–48 | stored +24 |
| 14 | `eq2_band_62hz` | 0–48 | stored +24 |
| 15 | `eq2_band_125hz` | 0–48 | stored +24 |
| 16 | `eq2_band_250hz` | 0–48 | stored +24 |
| 17 | `eq2_band_500hz` | 0–48 | stored +24 |
| 18 | `eq2_band_1khz` | 0–48 | stored +24 |
| 19 | `eq2_band_2khz` | 0–48 | stored +24 |
| 20 | `eq2_band_4khz` | 0–48 | stored +24 |
| 21 | `eq2_band_8khz` | 0–48 | stored +24 |
| 22 | `eq2_band_16khz` | 0–48 | stored +24 |
| 23 | `eq2_level` | 0–48 | stored +24 |

## `UserPatch%Patch_2` — 36 bytes

Base `0x60000620`. Byte 0 is the chain pattern (0–6; Tone Studio labels it
only with pictures, so it is not in `Param`). Bytes 4–29 are the colour
channels: which effect each colour (green/red/yellow) of each block holds,
the delay/reverb layer mode per colour, and each block's selected colour.

| Byte | Parameter | Stored | Notes |
|---|---|---|---|
| 1 | `send_return_position` | 0–1 |  |
| 2 | `eq_position` | 0–1 |  |
| 3 | `pedal_position` | 0–1 |  |
| 4 | `color_boost_green` | 0–25 |  |
| 5 | `color_boost_red` | 0–25 |  |
| 6 | `color_boost_yellow` | 0–25 |  |
| 7 | `color_mod_green` | 0–40 |  |
| 8 | `color_mod_red` | 0–40 |  |
| 9 | `color_mod_yellow` | 0–40 |  |
| 10 | `color_fx_green` | 0–40 |  |
| 11 | `color_fx_red` | 0–40 |  |
| 12 | `color_fx_yellow` | 0–40 |  |
| 13 | `color_delay_green` | 0–10 |  |
| 14 | `color_delay_red` | 0–10 |  |
| 15 | `color_delay_yellow` | 0–10 |  |
| 16 | `color_reverb_green` | 0–6 |  |
| 17 | `color_reverb_red` | 0–6 |  |
| 18 | `color_reverb_yellow` | 0–6 |  |
| 19 | `color_delay2_green` | 0–10 |  |
| 20 | `color_delay2_red` | 0–10 |  |
| 21 | `color_delay2_yellow` | 0–10 |  |
| 22 | `color_layer_green` | 0–2 |  |
| 23 | `color_layer_red` | 0–2 |  |
| 24 | `color_layer_yellow` | 0–2 |  |
| 25 | `color_select_boost` | 0–2 |  |
| 26 | `color_select_mod` | 0–2 |  |
| 27 | `color_select_fx` | 0–2 |  |
| 28 | `color_select_delay` | 0–2 |  |
| 29 | `color_select_reverb` | 0–2 |  |
| 35 | `cabinet_resonance` | 0–2 |  |

## `UserPatch%Status` — 18 bytes

Base `0x60000650`. Bytes 1–11 are the panel knob positions.

| Byte | Parameter | Stored | Notes |
|---|---|---|---|
| 0 | `panel_amp_type` | 0–4 | **read-only** |
| 12 | `variation` | 0–1 | **read-only** |
| 13 | `led_boost` | 0–3 | **read-only** |
| 14 | `led_mod` | 0–3 | **read-only** |
| 15 | `led_fx` | 0–3 | **read-only** |
| 16 | `led_delay` | 0–3 | **read-only** |
| 17 | `led_reverb` | 0–3 | **read-only** |

**LED colours**: `0` off · `1` green · `2` red · `3` yellow

These report which colour channel each section is on. Read-only on the amp.

## `UserPatch%Patch_Mk2V2` — 22 bytes

Base `0x60000F10`. Solo EQ and solo delay (MkII firmware 2.x). Byte 0 is
the solo EQ's position, not in `Param`: Tone Studio shows its two values
only as icons.

| Byte | Parameter | Stored | Notes |
|---|---|---|---|
| 1 | `solo_eq_switch` | 0–1 |  |
| 2 | `solo_eq_low_cut` | 0–17 |  |
| 3 | `solo_eq_low_gain` | 0–48 | stored +24 |
| 4 | `solo_eq_mid_freq` | 0–27 |  |
| 5 | `solo_eq_mid_q` | 0–5 |  |
| 6 | `solo_eq_mid_gain` | 0–48 | stored +24 |
| 7 | `solo_eq_high_gain` | 0–48 | stored +24 |
| 8 | `solo_eq_high_cut` | 0–14 |  |
| 9 | `solo_eq_level` | 0–48 | stored +24 |
| 10 | `solo_delay_switch` | 0–1 |  |
| 11 | `solo_delay_carryover` | 0–1 |  |
| 12 | `solo_delay_time` | 1–2000 | 2 bytes |
| 14 | `solo_delay_feedback` | 0–100 |  |
| 15 | `solo_delay_level` | 0–120 |  |
| 16 | `solo_delay_direct_mix` | 0–100 |  |
| 17 | `solo_delay_filter` | 0–2 |  |
| 18 | `solo_delay_high_cut` | 0–14 |  |
| 19 | `solo_delay_mod_switch` | 0–1 |  |
| 20 | `solo_delay_mod_rate` | 0–100 |  |
| 21 | `solo_delay_mod_depth` | 0–100 |  |

## `UserPatch%Contour(1)`–`(3)` — 2 bytes each

Base `0x60000F30`, `0x60000F38`, `0x60000F40`: byte 0 is the type (0–3),
byte 1 the frequency shift (stored 0–100, real −50…+50).

---

# Notes for a viewer

**Values are hex strings.** `["00", "0C", "64"]` → `[0, 12, 100]`. Every
byte is 0–127 (7-bit, a MIDI constraint).

**A file is a bank.** Show the patch list first, then one patch's detail.

**Three encodings to special-case:**
- Two-byte values — `hi*128+lo`: delay time, reverb pre-delay, a few effect settings
- Offsets — stored `value + offset` (EQ bands +24, boost bottom/tone +50, reverb time −1)
- Byte position vs address — see "Byte position is not address offset" above

**Ranges are not all 0–100.** `delay_level` goes to 120, `reverb_time` to
99, `limiter_ratio` to 17. Do not assume a percentage.

**Most of a patch is mapped.** `Param` names 553 settings.
What remains is assignments (knob, expression pedal, GA-FC), the second
EQ, solo EQ/delay and the colour assignments. A good viewer shows the known parameters as controls and
offers a raw hex dump for the rest, rather than pretending the gaps do not
exist.

**Amp types 28–32** are MkII-only and appear in no public documentation —
not even in Tone Studio, which shows the panel TYPE + VARIATION instead
(Status bytes 0 and 12). They are real — these Pantera and Children of
Bodom patches use them — but have no published names.

**Effect switches are separate from effect types.** A patch can have an
effect configured but switched off; show both.
