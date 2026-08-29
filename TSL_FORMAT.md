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
| `UserPatch%Eq(2)` | 24 | Duplicate view of the EQ in `Patch_0` |

**Note on `Eq(2)`:** it repeats bytes 48–71 of `Patch_0`. Read the EQ from
`Patch_0`; treat `Eq(2)` as redundant.

---

# Decoding each block

## `UserPatch%PatchName` — 16 bytes

ASCII, space-padded. `"folow the reaper"`, `"DIME'D"`, `"Southern Solo"`.

```js
name = bytes.map(b => String.fromCharCode(b)).join("").trim()
```

## `UserPatch%Patch_0` — 72 bytes

| Byte | Parameter | Range |
|---|---|---|
| 0 | `boost_switch` | 0–1 |
| 1 | `boost_type` | 0–25 |
| 2 | `boost_drive` | 0–100 |
| 3 | `boost_bottom` | 0–100 |
| 4 | `boost_tone` | 0–100 |
| 5 | `boost_solo_switch` | 0–1 |
| 6 | `boost_solo_level` | 0–100 |
| 7 | `boost_level` | 0–100 |
| 8 | `boost_direct_mix` | 0–100 |
| 17 | `amp_type` | 0–32 |
| 18 | `gain` | 0–100 |
| 19 | `knob_volume` | 0–100 |
| 20 | `bass` | 0–100 |
| 21 | `middle` | 0–100 |
| 22 | `treble` | 0–100 |
| 23 | `presence` | 0–100 |
| 24 | `volume` | 0–100 |
| 25 | `bright` | 0–1 |
| 48 | `eq_switch` | 0–1 |
| 49 | `eq_type` | 0–1 |
| 61 | `eq_band_31hz` | 0–48 |
| 62 | `eq_band_62hz` | 0–48 |
| 63 | `eq_band_125hz` | 0–48 |
| 64 | `eq_band_250hz` | 0–48 |
| 65 | `eq_band_500hz` | 0–48 |
| 66 | `eq_band_1khz` | 0–48 |
| 67 | `eq_band_2khz` | 0–48 |
| 68 | `eq_band_4khz` | 0–48 |
| 69 | `eq_band_8khz` | 0–48 |
| 70 | `eq_band_16khz` | 0–48 |
| 71 | `eq_level` | 0–48 |

**Boost pedal models** (20):  
`0`=Mid Boost · `1`=Clean Boost · `2`=Treble Boost · `3`=Crunch OD · `4`=Natural OD · `5`=Warm OD · `6`=Fat DS · `8`=Metal DS · `9`=Oct Fuzz · `10`=Blues Drive · `11`=Overdrive · `12`=T-Scream · `13`=Turbo OD · `14`=Distortion · `15`=Rat · `16`=Guv DS · `17`=DST+ · `18`=Metal Zone · `19`='60s Fuzz · `20`=Muff Fuzz

**Amp models** (33):  
`0`=Natural Clean · `1`=Full Range · `2`=Combo Crunch · `3`=Stack Crunch · `4`=HiGain Stack · `5`=Power Drive · `6`=Extreme Lead · `7`=Core Metal · `8`=JC-120 · `9`=Clean Twin · `10`=Pro Crunch · `11`=Tweed · `12`=Deluxe Crunch · `13`=VO Drive · `14`=VO Lead · `15`=Match Drive · `16`=BG Lead · `17`=BG Drive · `18`=MS1959 I · `19`=MS1959 I+II · `20`=R-Fire Vintage · `21`=R-Fire Modern · `22`=T-Amp Lead · `23`=SLDN · `24`=5150 Drive · `25`=Custom · `26`=BGNR UB · `27`=Orng RB · `28`=MkII amp 28 · `29`=MkII amp 29 · `30`=MkII amp 30 · `31`=MkII amp 31 · `32`=MkII amp 32

**Graphic EQ:** bytes 61–71 store **0–48 where 24 is flat**. Show as dB:
`dB = value - 24`, giving −24…+24. Band order is 31Hz, 62, 125, 250, 500,
1k, 2k, 4k, 8k, 16k, then overall level.

**`knob_volume` (byte 19)** is the physical volume knob. The amp reports it
but ignores writes — display only.

## `UserPatch%Fx(1)` and `Fx(2)` — 225 bytes each

| Byte | Parameter | Range |
|---|---|---|
| 0 | `fx1_switch` | 0–1 |
| 1 | `fx1_type` | 0–40 |
| 2 | `t_wah_mode` | 0–1 |
| 3 | `t_wah_polarity` | 0–1 |
| 4 | `t_wah_sens` | 0–100 |
| 5 | `t_wah_frequency` | 0–100 |
| 6 | `t_wah_peak` | 0–100 |
| 7 | `t_wah_direct_mix` | 0–100 |
| 8 | `t_wah_level` | 0–100 |
| 9 | `auto_wah_mode` | 0–1 |
| 10 | `auto_wah_frequency` | 0–100 |
| 11 | `auto_wah_peak` | 0–100 |
| 12 | `auto_wah_rate` | 0–100 |
| 13 | `auto_wah_depth` | 0–100 |
| 14 | `auto_wah_direct_mix` | 0–100 |
| 15 | `auto_wah_level` | 0–100 |
| 22 | `comp_type` | 0–6 |
| 23 | `comp_sustain` | 0–100 |
| 24 | `comp_attack` | 0–100 |
| 25 | `comp_tone` | 0–100 |
| 26 | `comp_level` | 0–100 |
| 27 | `limiter_type` | 0–2 |
| 28 | `limiter_attack` | 0–100 |
| 29 | `limiter_threshold` | 0–100 |
| 30 | `limiter_ratio` | 0–17 |
| 31 | `limiter_release` | 0–100 |
| 32 | `limiter_level` | 0–100 |
| 55 | `guitar_sim_type` | 0–7 |
| 56 | `guitar_sim_low` | 0–100 |
| 57 | `guitar_sim_high` | 0–100 |
| 58 | `guitar_sim_level` | 0–100 |
| 63 | `wave_synth_wave` | 0–1 |
| 64 | `wave_synth_cutoff` | 0–100 |
| 65 | `wave_synth_resonance` | 0–100 |
| 66 | `wave_synth_sens` | 0–100 |
| 67 | `wave_synth_decay` | 0–100 |
| 68 | `wave_synth_depth` | 0–100 |
| 69 | `wave_synth_level` | 0–100 |
| 71 | `octave_range` | 0–3 |
| 72 | `octave_level` | 0–100 |
| 73 | `octave_direct_mix` | 0–100 |

Byte 1 selects which effect is active. **Effects** (19):  
`0`=T Wah · `1`=Auto Wah · `2`=Pedal Wah · `3`=Comp · `4`=Limiter · `6`=Graphic EQ · `7`=Parametric EQ · `9`=Guitar Sim · `10`=Slow Gear · `12`=Wave Synth · `14`=Octave · `15`=Pitch Shifter · `16`=Harmonist · `18`=AC Processor · `19`=Phaser · `20`=Flanger · `21`=Tremolo · `22`=Rotary · `23`=Uni-V

The block holds settings for **every effect type at once**, not just the
selected one — so a viewer can show what a patch has dialled in for an
effect even when that effect is not currently active.

**Only the first ~74 bytes are mapped.** The remainder covers Pitch
Shifter, Harmonist, Slow Gear, AC Processor, Parametric EQ and the
modulation effects (Phaser, Flanger, Tremolo, Rotary, Uni-V, Slicer,
Vibrato, Ring Mod, Humanizer). Those use per-voice interval tables and
were mapped by probing the amp's live memory, at addresses that fall
outside this block — so their position *within the file* is not confirmed.
Do not guess them.

## `UserPatch%Delay(1)` / `Delay(2)` — 26 bytes each

| Byte | Parameter | Range |
|---|---|---|
| 0 | `delay_switch` | 0–1 |
| 1 | `delay_type` | 0–10 |
| 2 | `delay_time` | 1–2000 (2 bytes, big-endian 7-bit: `hi*128+lo`) |
| 4 | `delay_feedback` | 0–100 |
| 5 | `delay_high_cut` | 0–14 |
| 6 | `delay_level` | 0–120 |
| 7 | `delay_direct_mix` | 0–100 |

**Delay types**: `0`=Digital · `6`=Reverse · `7`=Analog · `8`=Tape Echo · `9`=Modulate

**Byte 2–3 is a 2-byte value**: `ms = bytes[2] * 128 + bytes[3]`, range
1–2000 ms. Every other value in the format is a single byte.

## `UserPatch%Patch_1` — 91 bytes

Reverb, the wah/expression pedal, and the noise gate.

| Byte | Parameter | Range |
|---|---|---|
| 0 | `reverb_switch` | 0–1 |
| 1 | `reverb_type` | 0–6 |
| 2 | `reverb_time` | 0–99 |
| 8 | `reverb_level` | 0–100 |
| 9 | `reverb_direct_mix` | 0–100 |
| 16 | `pedal_switch` | 0–1 |
| 17 | `pedal_type` | 0–2 |
| 18 | `wah_type` | 0–5 |
| 19 | `wah_position` | 0–100 |
| 20 | `wah_pedal_min` | 0–100 |
| 21 | `wah_pedal_max` | 0–100 |
| 22 | `wah_level` | 0–100 |
| 23 | `wah_direct_mix` | 0–100 |
| 38 | `noise_suppressor_switch` | 0–1 |
| 39 | `noise_suppressor_threshold` | 0–100 |
| 40 | `noise_suppressor_release` | 0–100 |

**Reverb types**: `0`=Room · `1`=Hall · `2`=Plate · `3`=Spring · `4`=Modulate · `5`=Reverb+Delay · `6`=Fast Decay  
**Pedal modes**: `0`=Wah · `1`=Pedal Bend · `2`=Wah 95E  
**Wah voicings**: `0`=Cry Wah · `1`=Vo Wah · `2`=Fat Wah · `3`=Light Wah · `4`=7String Wah · `5`=Reso Wah

## `UserPatch%Status` — 18 bytes

| Byte | Parameter | Range |
|---|---|---|
| 13 | `led_boost` | 0–3 |
| 14 | `led_mod` | 0–3 |
| 15 | `led_fx` | 0–3 |
| 16 | `led_delay` | 0–3 |
| 17 | `led_reverb` | 0–3 |

**LED colours**: `0`=off · `1`=green · `2`=red · `3`=yellow

These report which colour channel each section is on. Read-only on the amp.

---

# Notes for a viewer

**Values are hex strings.** `["00", "0C", "64"]` → `[0, 12, 100]`. Every
byte is 0–127 (7-bit, a MIDI constraint).

**A file is a bank.** Show the patch list first, then one patch's detail.

**Two encodings to special-case:**
- Delay time — 2 bytes, `hi*128+lo`, in ms
- EQ bands — stored 0–48, display as `value - 24` dB

**Ranges are not all 0–100.** `delay_level` goes to 120, `reverb_time` to
99, `limiter_ratio` to 17. Do not assume a percentage.

**Unmapped bytes are the majority.** Of ~2,200 bytes in a patch, about 110
are identified. A good viewer shows the known parameters as controls and
offers a raw hex dump for the rest, rather than pretending the gaps do not
exist.

**Amp types 28–32** are MkII-only and appear in no public documentation.
They are real — these Pantera and Children of Bodom patches use them — but
have no published names.

**Effect switches are separate from effect types.** A patch can have an
effect configured but switched off; show both.
