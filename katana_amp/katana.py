"""Control a BOSS Katana MkII amplifier over USB MIDI SysEx.

Reusable module: no printing, no CLI, no interactive prompts, so it can later
be driven headless from a Raspberry Pi UI. See demo.py for a usage example.

Protocol notes (verified against a Katana MkII 100W head):

  Every message is  F0 41 00 00 00 00 33 <op> <addr:4> <payload> <cksum> F7
  where op 0x11 = query and op 0x12 = set.

  On a query, the payload is a 4-byte length; the amp answers with a 0x12
  message carrying the data. On a set, the payload is the data itself.

  The MkII does NOT respond to the 0x00 00 04 xx "front panel" addresses
  documented for the first-generation Katana. Live amp parameters are at
  0x60 00 00 xx instead, laid out in the same field order. 0x10 00 00 xx
  holds the same structure for the currently selected channel/preset.
"""

import time

import mido

# --- Wire format -----------------------------------------------------------

MANUFACTURER_ID = 0x41  # Roland
MODEL_ID = (0x00, 0x00, 0x00, 0x33)
DEVICE_ID = 0x00

OP_QUERY = 0x11
OP_SET = 0x12

# Live ("temporary patch") area. Everything the amp is playing right now
# lives here; user patches 1-9 mirror the same layout at 0x10000000 up.
#
# Addresses below are the MkII map, cross-checked against the community
# address map on VGuitarForums and verified by read/write on a MkII 100W
# head. They are NOT the same as the 00 00 04 xx addresses documented for
# the first-generation Katana, which this amp ignores entirely.
LIVE_BASE = 0x60000000

OFFSET_NAME = 0x00  # 16 ASCII bytes
NAME_LENGTH = 16

# The 28 preamp models. The front-panel knob selects five of these; the
# rest ("sneaky amps") are reachable only over MIDI.
# Effect types for the FX1/FX2 slots. Pedal Wah (2) is the one that
# responds to a treadle position; T Wah and Auto Wah move on their own.
EFFECT_TYPES = {
    0x00: "T Wah",
    0x01: "Auto Wah",
    0x02: "Pedal Wah",
    0x03: "Comp",
    0x04: "Limiter",
    0x06: "Graphic EQ",
    0x07: "Parametric EQ",
    0x09: "Guitar Sim",
    0x0A: "Slow Gear",
    0x0C: "Wave Synth",
    0x0E: "Octave",
    0x0F: "Pitch Shifter",
    0x10: "Harmonist",
    0x12: "AC Processor",
    0x13: "Phaser",
    0x14: "Flanger",
    0x15: "Tremolo",
    0x16: "Rotary",
    0x17: "Uni-V",
}

# Pedal wah voicings, for fx*_wah_type.
WAH_TYPES = {
    0x00: "Cry Wah",
    0x01: "Vo Wah",
    0x02: "Fat Wah",
    0x03: "Light Wah",
    0x04: "7String Wah",
    0x05: "Reso Wah",
}

AMP_TYPES = {
    0x00: "Natural Clean",
    0x01: "Full Range",
    0x02: "Combo Crunch",
    0x03: "Stack Crunch",
    0x04: "HiGain Stack",
    0x05: "Power Drive",
    0x06: "Extreme Lead",
    0x07: "Core Metal",
    0x08: "JC-120",
    0x09: "Clean Twin",
    0x0A: "Pro Crunch",
    0x0B: "Tweed",
    0x0C: "Deluxe Crunch",
    0x0D: "VO Drive",
    0x0E: "VO Lead",
    0x0F: "Match Drive",
    0x10: "BG Lead",
    0x11: "BG Drive",
    0x12: "MS1959 I",
    0x13: "MS1959 I+II",
    0x14: "R-Fire Vintage",
    0x15: "R-Fire Modern",
    0x16: "T-Amp Lead",
    0x17: "SLDN",
    0x18: "5150 Drive",
    0x19: "Custom",
    0x1A: "BGNR UB",
    0x1B: "Orng RB",
    # 28-32 are accepted by the MkII but appear in no public table. Boss
    # Tone Studio patches do use them (0x20 shows up in .tsl files), so
    # they are almost certainly the MkII's added preamp models.
    0x1C: "MkII amp 28",
    0x1D: "MkII amp 29",
    0x1E: "MkII amp 30",
    0x1F: "MkII amp 31",
    0x20: "MkII amp 32",
}

# name -> (absolute address, low, high). Every entry below was verified by
# writing to the amp and reading the value back.
PARAMETERS = {
    # --- Amp -------------------------------------------------------------
    "amp_type": (0x60000021, 0x00, 0x20),
    "gain": (0x60000022, 0x00, 0x64),
    # 0x60000023 follows the physical volume knob and ignores writes, so the
    # writable "volume" is master volume at 0x60000028.
    "knob_volume": (0x60000023, 0x00, 0x64),
    "bass": (0x60000024, 0x00, 0x64),
    "middle": (0x60000025, 0x00, 0x64),
    "treble": (0x60000026, 0x00, 0x64),
    "presence": (0x60000027, 0x00, 0x64),
    "volume": (0x60000028, 0x00, 0x64),
    "bright": (0x60000029, 0x00, 0x01),

    # --- Boost / overdrive ----------------------------------------------
    "boost_switch": (0x60000010, 0x00, 0x01),
    "boost_type": (0x60000011, 0x00, 0x19),
    "boost_drive": (0x60000012, 0x00, 0x64),
    "boost_bottom": (0x60000013, 0x00, 0x64),
    "boost_tone": (0x60000014, 0x00, 0x64),
    "boost_solo_switch": (0x60000015, 0x00, 0x01),
    "boost_solo_level": (0x60000016, 0x00, 0x64),
    "boost_level": (0x60000017, 0x00, 0x64),
    "boost_direct_mix": (0x60000018, 0x00, 0x64),

    # --- EQ ---------------------------------------------------------------
    "eq_switch": (0x60000040, 0x00, 0x01),
    "eq_type": (0x60000041, 0x00, 0x01),

    # --- Effect slots ------------------------------------------------------
    "fx1_switch": (0x60000100, 0x00, 0x01),
    "fx1_type": (0x60000101, 0x00, 0x28),
    "fx2_switch": (0x60000300, 0x00, 0x01),
    "fx2_type": (0x60000301, 0x00, 0x28),

    # --- Delay 1 ----------------------------------------------------------
    "delay_switch": (0x60000500, 0x00, 0x01),
    "delay_type": (0x60000501, 0x00, 0x0A),
    "delay_feedback": (0x60000504, 0x00, 0x64),
    "delay_high_cut": (0x60000505, 0x00, 0x0E),
    "delay_level": (0x60000506, 0x00, 0x78),
    "delay_direct_mix": (0x60000507, 0x00, 0x64),

    # --- Delay 2 (a second, independent delay engine) ---------------------
    "delay2_switch": (0x60000520, 0x00, 0x01),
    "delay2_type": (0x60000521, 0x00, 0x0A),
    "delay2_feedback": (0x60000524, 0x00, 0x64),
    "delay2_high_cut": (0x60000525, 0x00, 0x0E),
    "delay2_level": (0x60000526, 0x00, 0x78),
    "delay2_direct_mix": (0x60000527, 0x00, 0x64),

    # --- Graphic EQ (10 bands) --------------------------------------------
    # 0-48, where 24 is flat. The helpers in controls.py take dB (-12..+12).
    "eq_band_31hz": (0x6000004D, 0x00, 0x30),
    "eq_band_62hz": (0x6000004E, 0x00, 0x30),
    "eq_band_125hz": (0x6000004F, 0x00, 0x30),
    "eq_band_250hz": (0x60000050, 0x00, 0x30),
    "eq_band_500hz": (0x60000051, 0x00, 0x30),
    "eq_band_1khz": (0x60000052, 0x00, 0x30),
    "eq_band_2khz": (0x60000053, 0x00, 0x30),
    "eq_band_4khz": (0x60000054, 0x00, 0x30),
    "eq_band_8khz": (0x60000055, 0x00, 0x30),
    "eq_band_16khz": (0x60000056, 0x00, 0x30),
    "eq_level": (0x60000057, 0x00, 0x30),

    # --- Per-effect parameters --------------------------------------------
    # Each effect keeps its own block, whatever the slot is currently set
    # to, so these can be dialled in before switching the slot to them.
    # FX2 mirrors FX1 at +0x200.
    # Touch wah / auto wah (the FX-slot wahs, distinct from the pedal wah)
    "t_wah_mode": (0x60000102, 0x00, 0x01),
    "t_wah_polarity": (0x60000103, 0x00, 0x01),
    "t_wah_sens": (0x60000104, 0x00, 0x64),
    "t_wah_frequency": (0x60000105, 0x00, 0x64),
    "t_wah_peak": (0x60000106, 0x00, 0x64),
    "t_wah_direct_mix": (0x60000107, 0x00, 0x64),
    "t_wah_level": (0x60000108, 0x00, 0x64),

    "auto_wah_mode": (0x60000109, 0x00, 0x01),
    "auto_wah_frequency": (0x6000010A, 0x00, 0x64),
    "auto_wah_peak": (0x6000010B, 0x00, 0x64),
    "auto_wah_rate": (0x6000010C, 0x00, 0x64),
    "auto_wah_depth": (0x6000010D, 0x00, 0x64),
    "auto_wah_direct_mix": (0x6000010E, 0x00, 0x64),
    "auto_wah_level": (0x6000010F, 0x00, 0x64),

    # Compressor
    "comp_type": (0x60000116, 0x00, 0x06),
    "comp_sustain": (0x60000117, 0x00, 0x64),
    "comp_attack": (0x60000118, 0x00, 0x64),
    "comp_tone": (0x60000119, 0x00, 0x64),
    "comp_level": (0x6000011A, 0x00, 0x64),

    # Limiter
    "limiter_type": (0x6000011B, 0x00, 0x02),
    "limiter_attack": (0x6000011C, 0x00, 0x64),
    "limiter_threshold": (0x6000011D, 0x00, 0x64),
    "limiter_ratio": (0x6000011E, 0x00, 0x11),
    "limiter_release": (0x6000011F, 0x00, 0x64),
    "limiter_level": (0x60000120, 0x00, 0x64),

    # Guitar simulator
    "guitar_sim_type": (0x60000137, 0x00, 0x07),
    "guitar_sim_low": (0x60000138, 0x00, 0x64),
    "guitar_sim_high": (0x60000139, 0x00, 0x64),
    "guitar_sim_level": (0x6000013A, 0x00, 0x64),

    # Wave synth
    "wave_synth_wave": (0x6000013F, 0x00, 0x01),
    "wave_synth_cutoff": (0x60000140, 0x00, 0x64),
    "wave_synth_resonance": (0x60000141, 0x00, 0x64),
    "wave_synth_sens": (0x60000142, 0x00, 0x64),
    "wave_synth_decay": (0x60000143, 0x00, 0x64),
    "wave_synth_depth": (0x60000144, 0x00, 0x64),
    "wave_synth_level": (0x60000145, 0x00, 0x64),

    # Octave
    "octave_range": (0x60000147, 0x00, 0x03),
    "octave_level": (0x60000148, 0x00, 0x64),
    "octave_direct_mix": (0x60000149, 0x00, 0x64),

    "phaser_type": (0x60000203, 0x00, 0x03),
    "phaser_rate": (0x60000204, 0x00, 0x64),
    "phaser_depth": (0x60000205, 0x00, 0x64),
    "phaser_manual": (0x60000206, 0x00, 0x64),
    "phaser_resonance": (0x60000207, 0x00, 0x64),
    "phaser_step_rate": (0x60000208, 0x00, 0x64),
    "phaser_level": (0x60000209, 0x00, 0x64),
    "phaser_direct_mix": (0x6000020A, 0x00, 0x64),

    "flanger_rate": (0x6000020B, 0x00, 0x64),
    "flanger_depth": (0x6000020C, 0x00, 0x64),
    "flanger_manual": (0x6000020D, 0x00, 0x64),
    "flanger_resonance": (0x6000020E, 0x00, 0x64),
    "flanger_low_cut": (0x60000210, 0x00, 0x0A),
    "flanger_level": (0x60000211, 0x00, 0x64),
    "flanger_direct_mix": (0x60000212, 0x00, 0x64),

    "rotary_rate_fast": (0x60000219, 0x00, 0x64),
    "rotary_depth": (0x6000021C, 0x00, 0x64),
    "rotary_level": (0x6000021D, 0x00, 0x64),

    "slicer_pattern": (0x60000221, 0x00, 0x13),
    "slicer_rate": (0x60000222, 0x00, 0x64),
    "slicer_trigger_sens": (0x60000223, 0x00, 0x64),
    "slicer_level": (0x60000224, 0x00, 0x64),
    "slicer_direct_mix": (0x60000225, 0x00, 0x64),

    "ring_mod_mode": (0x6000022B, 0x00, 0x01),
    "ring_mod_frequency": (0x6000022C, 0x00, 0x64),
    "ring_mod_level": (0x6000022D, 0x00, 0x64),
    "ring_mod_direct_mix": (0x6000022E, 0x00, 0x64),

    "humanizer_mode": (0x6000022F, 0x00, 0x01),
    "humanizer_vowel1": (0x60000230, 0x00, 0x04),
    "humanizer_vowel2": (0x60000231, 0x00, 0x04),
    "humanizer_sens": (0x60000232, 0x00, 0x64),
    "humanizer_rate": (0x60000233, 0x00, 0x64),
    "humanizer_depth": (0x60000234, 0x00, 0x64),
    "humanizer_manual": (0x60000235, 0x00, 0x64),
    "humanizer_level": (0x60000236, 0x00, 0x64),

    "uni_v_rate": (0x6000021E, 0x00, 0x64),
    "uni_v_depth": (0x6000021F, 0x00, 0x64),
    "uni_v_level": (0x60000220, 0x00, 0x64),

    "vibrato_rate": (0x60000226, 0x00, 0x64),
    "vibrato_depth": (0x60000227, 0x00, 0x64),
    "vibrato_level": (0x6000022A, 0x00, 0x64),

    "tremolo_waveshape": (0x60000213, 0x00, 0x64),
    "tremolo_rate": (0x60000214, 0x00, 0x64),
    "tremolo_depth": (0x60000215, 0x00, 0x64),
    "tremolo_level": (0x60000216, 0x00, 0x64),

    # --- Channel / colour state --------------------------------------------
    # These store and read back, but writing them does NOT change the panel
    # LEDs or the sound on a MkII - tested on hardware. They appear to be a
    # status mirror the amp maintains, not a control. Kept because they are
    # useful to READ (they tell you which colour channel is selected).
    # Do not expect a write here to do anything audible or visible.
    "led_boost": (0x6000065D, 0x00, 0x03),
    "led_mod": (0x6000065E, 0x00, 0x03),
    "led_fx": (0x6000065F, 0x00, 0x03),
    "led_delay": (0x60000660, 0x00, 0x03),
    "led_reverb": (0x60000661, 0x00, 0x03),

    # --- Noise suppressor --------------------------------------------------
    "noise_suppressor_switch": (0x60000566, 0x00, 0x01),
    "noise_suppressor_threshold": (0x60000567, 0x00, 0x64),
    "noise_suppressor_release": (0x60000568, 0x00, 0x64),

    # --- Reverb -----------------------------------------------------------
    "reverb_switch": (0x60000540, 0x00, 0x01),
    "reverb_type": (0x60000541, 0x00, 0x06),
    "reverb_time": (0x60000542, 0x00, 0x63),
    "reverb_level": (0x60000548, 0x00, 0x64),
    "reverb_direct_mix": (0x60000549, 0x00, 0x64),

    # --- Pedal FX / wah ----------------------------------------------------
    # This is the real wah, on its own pedal section - not an FX slot.
    "pedal_switch": (0x60000550, 0x00, 0x01),
    "pedal_type": (0x60000551, 0x00, 0x02),
    "wah_type": (0x60000552, 0x00, 0x05),
    "wah_position": (0x60000553, 0x00, 0x64),
    "wah_pedal_min": (0x60000554, 0x00, 0x64),
    "wah_pedal_max": (0x60000555, 0x00, 0x64),
    "wah_level": (0x60000556, 0x00, 0x64),
    "wah_direct_mix": (0x60000557, 0x00, 0x64),
}

# Channel colours as reported by the led_* parameters. The numbers are what
# the amp reports; the colour names are the documented convention and are
# unconfirmed by eye. Writing these does not move the panel LEDs.
LED_COLOURS = {0x00: "off", 0x01: "green", 0x02: "red", 0x03: "yellow"}

# Parameters stored as two 7-bit bytes: value = high * 128 + low.
# Delay time is in milliseconds.
WIDE_PARAMETERS = {
    "delay_time": (0x60000502, 1, 2000),
    "delay2_time": (0x60000522, 1, 2000),
}

# The pedal wah voicings, for wah_type.
WAH_TYPES = {
    0x00: "Cry Wah",
    0x01: "Vo Wah",
    0x02: "Fat Wah",
    0x03: "Light Wah",
    0x04: "7String Wah",
    0x05: "Reso Wah",
}

# What the expression pedal section is doing, for pedal_type.
PEDAL_TYPES = {0x00: "Wah", 0x01: "Pedal Bend", 0x02: "Wah 95E"}

BOOST_TYPES = {
    0x00: "Mid Boost", 0x01: "Clean Boost", 0x02: "Treble Boost",
    0x03: "Crunch OD", 0x04: "Natural OD", 0x05: "Warm OD",
    0x06: "Fat DS", 0x08: "Metal DS", 0x09: "Oct Fuzz",
    0x0A: "Blues Drive", 0x0B: "Overdrive", 0x0C: "T-Scream",
    0x0D: "Turbo OD", 0x0E: "Distortion", 0x0F: "Rat",
    0x10: "Guv DS", 0x11: "DST+", 0x12: "Metal Zone",
    0x13: "'60s Fuzz", 0x14: "Muff Fuzz",
}

# Reverb types, also from the first-generation docs - numbers verified,
# names unconfirmed on the MkII.
REVERB_TYPES = {
    0x00: "Room", 0x01: "Hall", 0x02: "Plate",
    0x03: "Spring", 0x04: "Modulate", 0x05: "Reverb+Delay", 0x06: "Fast Decay",
}

# Delay types. The amp accepts 0-10 but reports only numbers, and no
# MkII source lists the names, so these come from the first-generation
# docs and are the least certain table here. Check against BOSS Tone
# Studio if a name looks wrong; the numbers themselves are correct.
DELAY_TYPES = {
    0x00: "Digital",
    0x06: "Reverse",
    0x07: "Analog",
    0x08: "Tape Echo",
    0x09: "Modulate",
}

def checksum(payload):
    """Roland 7-bit checksum over the address + data bytes."""
    total = 0
    for byte in payload:
        total = (total + byte) & 0x7F
    return (0x80 - total) & 0x7F


def _encode_length(length):
    """Encode a byte count as Roland's 4-byte 7-bit value."""
    return [
        (length // 0x200000) % 0x80,
        (length // 0x4000) % 0x80,
        (length // 0x80) % 0x80,
        length % 0x80,
    ]


def find_ports():
    """Return the MIDI port names that look like a Katana."""
    return [name for name in mido.get_output_names() if "KATANA" in name.upper()]


# Which named-value table each parameter draws from. Everything not listed
# here is a plain number (or a 0/1 switch, when its range is 0-1).
ENUMS = {
    "amp_type": "AMP_TYPES",
    "boost_type": "BOOST_TYPES",
    "fx1_type": "EFFECT_TYPES",
    "fx2_type": "EFFECT_TYPES",
    "delay_type": "DELAY_TYPES",
    "delay2_type": "DELAY_TYPES",
    "reverb_type": "REVERB_TYPES",
    "wah_type": "WAH_TYPES",
    "pedal_type": "PEDAL_TYPES",
    "led_boost": "LED_COLOURS",
    "led_mod": "LED_COLOURS",
    "led_fx": "LED_COLOURS",
    "led_delay": "LED_COLOURS",
    "led_reverb": "LED_COLOURS",
}

# Parameters the amp reports but ignores writes to.
READ_ONLY = frozenset(
    {"knob_volume", "led_boost", "led_mod", "led_fx", "led_delay", "led_reverb"}
)

# Parameters stored with an offset, exposed in real units.
# name -> (offset, unit); value_shown = value_stored - offset
OFFSETS = {name: (24, "dB") for name in PARAMETERS if name.startswith("eq_band_")}

UNITS = {"delay_time": "ms", "delay2_time": "ms"}

# Graphic EQ bands low to high - the order a fader row should show them in,
# which is not the alphabetical order the parameter table happens to give.
EQ_BANDS_ORDER = [
    "eq_band_31hz", "eq_band_62hz", "eq_band_125hz", "eq_band_250hz",
    "eq_band_500hz", "eq_band_1khz", "eq_band_2khz", "eq_band_4khz",
    "eq_band_8khz", "eq_band_16khz",
]


def parameter_group(name):
    """The section a parameter belongs to, for grouping in a UI."""
    for prefix, group in (
        ("eq_band_", "eq"), ("eq_", "eq"), ("boost_", "boost"),
        ("delay2_", "delay2"), ("delay_", "delay"), ("reverb_", "reverb"),
        ("wah_", "wah"), ("pedal_", "wah"), ("fx1_", "fx1"), ("fx2_", "fx2"),
        ("noise_suppressor_", "noise_gate"), ("led_", "channels"),
        ("phaser_", "effects"), ("flanger_", "effects"), ("tremolo_", "effects"),
        ("vibrato_", "effects"), ("uni_v_", "effects"), ("rotary_", "effects"),
        ("slicer_", "effects"), ("ring_mod_", "effects"),
        ("humanizer_", "effects"), ("t_wah_", "effects"),
        ("auto_wah_", "effects"), ("comp_", "effects"),
        ("limiter_", "effects"), ("guitar_sim_", "effects"),
        ("wave_synth_", "effects"), ("octave_", "effects"),
    ):
        if name.startswith(prefix):
            return group
    return "amp"


def describe_parameters():
    """Return the full parameter schema, ready to serialise as JSON."""
    tables = {
        "AMP_TYPES": AMP_TYPES, "BOOST_TYPES": BOOST_TYPES,
        "EFFECT_TYPES": EFFECT_TYPES, "DELAY_TYPES": DELAY_TYPES,
        "REVERB_TYPES": REVERB_TYPES, "WAH_TYPES": WAH_TYPES,
        "PEDAL_TYPES": PEDAL_TYPES, "LED_COLOURS": LED_COLOURS,
    }

    schema = []
    everything = dict(PARAMETERS)
    everything.update(WIDE_PARAMETERS)

    for name, (_, low, high) in sorted(everything.items()):
        offset, unit = OFFSETS.get(name, (0, None))
        entry = {
            "name": name,
            "group": parameter_group(name),
            "min": low - offset,
            "max": high - offset,
            "writable": name not in READ_ONLY,
        }
        if unit or name in UNITS:
            entry["unit"] = unit or UNITS[name]

        if name in ENUMS:
            entry["kind"] = "enum"
            entry["options"] = {
                str(value): label for value, label in tables[ENUMS[name]].items()
            }
        elif low == 0 and high == 1:
            entry["kind"] = "toggle"
        else:
            entry["kind"] = "range"

        schema.append(entry)
    return schema


# Program Change numbers for channel selection, from the official manual's
# "RECOGNIZED RECEIVE DATA" table. These are what actually switch channels -
# writing the led_* addresses does not.
CHANNELS = {
    "a1": 1, "a2": 2, "a3": 3, "a4": 4, "panel": 5,
    "b1": 6, "b2": 7, "b3": 8, "b4": 9,
}

# Control Change numbers, also from the manual. 0-63 = off, 64-127 = on.
CONTROL_CHANGES = {
    "boost": 16, "mod": 17, "fx": 18, "delay": 19,
    "reverb": 20, "effect_loop": 21,
}

# Expression / footswitch CCs, 0-127.
EXPRESSION_CC = {
    "ga_fc_exp1": 80, "ga_fc_exp2": 81, "exp_pedal": 82,
    "ga_fc_fs1": 83, "ga_fc_fs2": 84,
}


class KatanaError(Exception):
    """Raised when the amp cannot be reached or does not answer."""


class Katana:
    """A connection to one Katana amplifier.

    Usable as a context manager so the MIDI ports always get closed:

        with Katana() as amp:
            print(amp.read_panel())
    """

    def __init__(self, port_name=None, timeout=1.0, midi_channel=1):
        if port_name is None:
            found = find_ports()
            if not found:
                raise KatanaError(
                    "No Katana MIDI port found. Is the amp powered on and "
                    "connected over USB?"
                )
            # MIDI 1 is the SysEx control port; it sorts first.
            port_name = found[0]

        self.port_name = port_name
        self.timeout = timeout
        # The amp's MIDI receive channel, 0-based. Factory default is CH 1;
        # it is chosen by holding a CH button while powering on.
        self.midi_channel = midi_channel - 1
        try:
            self._out = mido.open_output(port_name)
            self._in = mido.open_input(port_name)
        except (IOError, OSError) as exc:
            raise KatanaError(f"Could not open MIDI port {port_name!r}: {exc}")

    # --- lifecycle ---------------------------------------------------------

    def close(self):
        for port in (self._out, self._in):
            if port is not None and not port.closed:
                port.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False

    # --- raw SysEx ---------------------------------------------------------

    def _send(self, op, address, payload):
        body = list(address) + list(payload)
        # Header is fixed: 41 00 00 00 00 33 <op>
        data = [MANUFACTURER_ID, DEVICE_ID, *MODEL_ID, op]
        self._out.send(mido.Message("sysex", data=data + body + [checksum(body)]))

    def read(self, address, length, attempts=3):
        """Query `length` bytes at `address`; return them as a list of ints.

        The amp occasionally drops a reply when it is busy - especially
        while a burst of writes is still settling - so a timed-out read is
        retried rather than reported as a missing address.
        """
        for attempt in range(attempts):
            # Drop anything the amp sent unprompted so we read our own reply.
            for _ in self._in.iter_pending():
                pass

            self._send(OP_QUERY, address, _encode_length(length))

            deadline = time.time() + self.timeout
            received = {}
            while time.time() < deadline:
                message = self._in.poll()
                if message is None:
                    time.sleep(0.005)
                    continue
                if message.type != "sysex":
                    continue
                # mido strips the leading F0, so: 41 00 00 00 00 33 12 <addr:4> ...
                data = list(message.data)
                offset = data[7:11]
                chunk = data[11:-1]
                # Key each chunk by its position relative to what we asked for,
                # so multi-chunk replies reassemble in the right order.
                start = Katana._decode_address(offset) - Katana._decode_address(address)
                received[start] = chunk
                if sum(len(c) for c in received.values()) >= length:
                    break

            if received:
                result = []
                for start in sorted(received):
                    result.extend(received[start])
                return result[:length]

            if attempt + 1 < attempts:
                time.sleep(0.05 * (attempt + 1))

        raise KatanaError(
            f"No reply from the amp for address "
            f"{' '.join(f'{b:02X}' for b in address)} after {attempts} attempts."
        )

    def write(self, address, data):
        """Set the bytes at `address`. Fire-and-forget; the amp does not ack."""
        self._send(OP_SET, address, list(data))

    # --- parameters --------------------------------------------------------

    @staticmethod
    def _decode_address(address):
        """Collapse a 4-byte 7-bit address into a single integer."""
        a, b, c, d = address
        return (a << 21) | (b << 14) | (c << 7) | d

    @staticmethod
    def _encode_address(value):
        """Split an absolute address into its four 7-bit SysEx bytes."""
        return (
            (value >> 24) & 0x7F,
            (value >> 16) & 0x7F,
            (value >> 8) & 0x7F,
            value & 0x7F,
        )

    def get_parameter(self, name):
        """Read one named parameter (see PARAMETERS)."""
        address, _, _ = self._lookup(name)
        return self.read(self._encode_address(address), 1)[0]

    def set_parameter(self, name, value):
        """Write one named parameter, refusing values the amp would clamp."""
        address, low, high = self._lookup(name)
        if not isinstance(value, int):
            raise KatanaError(f"{name} must be an integer, got {value!r}")
        if not low <= value <= high:
            raise KatanaError(f"{name} must be between {low} and {high}, got {value}")
        self.write(self._encode_address(address), [value])

    @staticmethod
    def _lookup(name):
        try:
            return PARAMETERS[name]
        except KeyError:
            known = ", ".join(sorted(PARAMETERS))
            raise KatanaError(f"Unknown parameter {name!r}. Known: {known}")

    def get_wide_parameter(self, name):
        """Read a two-byte parameter, e.g. delay time in milliseconds."""
        address, _, _ = self._lookup_wide(name)
        high, low = self.read(self._encode_address(address), 2)
        return high * 128 + low

    def set_wide_parameter(self, name, value):
        """Write a two-byte parameter, e.g. delay time in milliseconds."""
        address, low_limit, high_limit = self._lookup_wide(name)
        if not isinstance(value, int):
            raise KatanaError(f"{name} must be an integer, got {value!r}")
        if not low_limit <= value <= high_limit:
            raise KatanaError(
                f"{name} must be between {low_limit} and {high_limit}, got {value}"
            )
        self.write(self._encode_address(address), [value // 128, value % 128])

    @staticmethod
    def _lookup_wide(name):
        try:
            return WIDE_PARAMETERS[name]
        except KeyError:
            known = ", ".join(sorted(WIDE_PARAMETERS))
            raise KatanaError(f"Unknown wide parameter {name!r}. Known: {known}")

    def read_patch_name(self):
        """Return the name of the patch currently loaded on the amp."""
        raw = self.read(self._encode_address(LIVE_BASE + OFFSET_NAME), NAME_LENGTH)
        return "".join(chr(b) for b in raw if 0x20 <= b < 0x7F).strip()

    def read_panel(self):
        """Read the amp section in one pass. Returns a dict."""
        settings = {"patch_name": self.read_patch_name()}

        block = self.read(self._encode_address(0x60000020), 0x10)
        for param, (address, _, _) in PARAMETERS.items():
            index = address - 0x60000020
            if 0 <= index < len(block):
                settings[param] = block[index]

        amp_type = settings.get("amp_type")
        settings["amp_type_name"] = AMP_TYPES.get(amp_type, f"Variation {amp_type}")
        return settings

    def select_channel(self, channel):
        """Switch tone-setting channel with a Program Change.

        `channel` is a name from CHANNELS ("a1".."a4", "panel", "b1".."b4")
        or a raw program number 1-9. This is the documented way to change
        channels; the led_* parameters only report the result.
        """
        if isinstance(channel, str):
            key = channel.lower().replace(" ", "").replace("ch", "")
            if key not in CHANNELS:
                known = ", ".join(CHANNELS)
                raise KatanaError(f"Unknown channel {channel!r}. Known: {known}")
            program = CHANNELS[key]
        else:
            program = channel
        if not 1 <= program <= 9:
            raise KatanaError(f"Channel program must be 1-9, got {program}")
        self._out.send(
            mido.Message("program_change", channel=self.midi_channel, program=program - 1)
        )
        return program

    def send_control_change(self, control, value):
        """Send a raw Control Change on the amp's receive channel."""
        if not 0 <= value <= 127:
            raise KatanaError(f"CC value must be 0-127, got {value}")
        self._out.send(
            mido.Message(
                "control_change", channel=self.midi_channel,
                control=control, value=value,
            )
        )

    def switch_effect(self, name, on):
        """Turn an effect block on or off using the documented CC messages."""
        try:
            control = CONTROL_CHANGES[name]
        except KeyError:
            known = ", ".join(sorted(CONTROL_CHANGES))
            raise KatanaError(f"Unknown effect {name!r}. Known: {known}")
        self.send_control_change(control, 127 if on else 0)
        return bool(on)

    # --- Patch memory ------------------------------------------------------
    #
    # User patches 1-9 mirror the live area's layout, starting at
    # 0x10000000 and 0x10000 apart. Writing there edits the stored sound
    # without disturbing what is playing.

    PATCH_BASE = 0x10000000
    PATCH_STRIDE = 0x10000

    @staticmethod
    def patch_address(patch, offset=0):
        """Absolute address of `offset` within stored patch 1-9."""
        if not 1 <= patch <= 9:
            raise KatanaError(f"Patch must be 1-9, got {patch}")
        return Katana.PATCH_BASE + (patch - 1) * Katana.PATCH_STRIDE + offset

    def read_patch(self, patch, offset=0, length=1):
        """Read bytes from a stored patch."""
        return self.read(self._encode_address(self.patch_address(patch, offset)), length)

    def write_patch(self, patch, offset, data):
        """Write bytes into a stored patch."""
        self.write(self._encode_address(self.patch_address(patch, offset)), data)

    # The regions a patch actually occupies, as (start, length) offsets from
    # the base of the patch. The amp leaves gaps between them and does not
    # answer reads there, so a full copy has to skip those.
    PATCH_REGIONS = ((0x000, 0x740), (0x780, 0x040), (0x800, 0x100))

    def copy_live_to_patch(self, patch, chunk=0x20):
        """Copy the entire live sound into stored patch 1-9.

        Copies every region the patch occupies - amp, effects, EQ, delays,
        reverb and the rest - not just the amp block. Returns the number of
        bytes written.
        """
        written = 0
        for start, length in self.PATCH_REGIONS:
            for offset in range(start, start + length, chunk):
                size = min(chunk, start + length - offset)
                block = self.read(self._encode_address(LIVE_BASE + offset), size)
                if not block:
                    continue
                self.write_patch(patch, offset, block)
                written += len(block)
        return written

    def identify(self):
        """Send a universal Identity Request; return the raw reply bytes."""
        for _ in self._in.iter_pending():
            pass
        self._out.send(mido.Message("sysex", data=[0x7E, 0x7F, 0x06, 0x01]))

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            message = self._in.poll()
            if message is not None and message.type == "sysex":
                return list(message.data)
            time.sleep(0.005)
        raise KatanaError("The amp did not answer the identity request.")
