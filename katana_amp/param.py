"""Every setting the Katana MkII exposes, as an enum.

    from katana_amp.param import Param

    Param("gain")                Param.GAIN       (like Param::from('gain'))
    Param.GAIN.value             "gain"
    Param.GAIN.address()         0x60000022
    Param.GAIN.kind()            Kind.RANGE
    Param.GAIN.range()           (0, 100)
    Param.AMP_TYPE.options()[8]  "JC-120"
    Param.schema()               every setting, for the UI

The addresses are the MkII's live area at 0x60000000 (see katana.py).
"""

from enum import StrEnum

from katana_amp.kind import Kind


class Param(StrEnum):
    """Every setting the amp exposes. The value is its name, e.g. "gain"."""

    # --- Amp -------------------------------------------------------------
    AMP_TYPE = "amp_type"
    GAIN = "gain"
    # 0x60000023 follows the physical volume knob and ignores writes, so the
    # writable "volume" is master volume at 0x60000028.
    KNOB_VOLUME = "knob_volume"
    BASS = "bass"
    MIDDLE = "middle"
    TREBLE = "treble"
    PRESENCE = "presence"
    VOLUME = "volume"
    BRIGHT = "bright"

    # --- Boost / overdrive ----------------------------------------------
    BOOST_SWITCH = "boost_switch"
    BOOST_TYPE = "boost_type"
    BOOST_DRIVE = "boost_drive"
    BOOST_BOTTOM = "boost_bottom"
    BOOST_TONE = "boost_tone"
    BOOST_SOLO_SWITCH = "boost_solo_switch"
    BOOST_SOLO_LEVEL = "boost_solo_level"
    BOOST_LEVEL = "boost_level"
    BOOST_DIRECT_MIX = "boost_direct_mix"

    # --- EQ ---------------------------------------------------------------
    EQ_SWITCH = "eq_switch"
    EQ_TYPE = "eq_type"

    # --- Effect slots ------------------------------------------------------
    FX1_SWITCH = "fx1_switch"
    FX1_TYPE = "fx1_type"
    FX2_SWITCH = "fx2_switch"
    FX2_TYPE = "fx2_type"

    # --- Delay 1 ----------------------------------------------------------
    DELAY_SWITCH = "delay_switch"
    DELAY_TYPE = "delay_type"
    DELAY_TIME = "delay_time"
    DELAY_FEEDBACK = "delay_feedback"
    DELAY_HIGH_CUT = "delay_high_cut"
    DELAY_LEVEL = "delay_level"
    DELAY_DIRECT_MIX = "delay_direct_mix"

    # --- Delay 2 (a second, independent delay engine) ---------------------
    DELAY2_SWITCH = "delay2_switch"
    DELAY2_TYPE = "delay2_type"
    DELAY2_TIME = "delay2_time"
    DELAY2_FEEDBACK = "delay2_feedback"
    DELAY2_HIGH_CUT = "delay2_high_cut"
    DELAY2_LEVEL = "delay2_level"
    DELAY2_DIRECT_MIX = "delay2_direct_mix"

    # --- Graphic EQ (10 bands) --------------------------------------------
    # Stored 0-48, where 24 is flat; offset=24 turns that into -24..+24 dB.
    EQ_BAND_31HZ = "eq_band_31hz"
    EQ_BAND_62HZ = "eq_band_62hz"
    EQ_BAND_125HZ = "eq_band_125hz"
    EQ_BAND_250HZ = "eq_band_250hz"
    EQ_BAND_500HZ = "eq_band_500hz"
    EQ_BAND_1KHZ = "eq_band_1khz"
    EQ_BAND_2KHZ = "eq_band_2khz"
    EQ_BAND_4KHZ = "eq_band_4khz"
    EQ_BAND_8KHZ = "eq_band_8khz"
    EQ_BAND_16KHZ = "eq_band_16khz"
    EQ_LEVEL = "eq_level"

    # --- Per-effect parameters --------------------------------------------
    # Each effect keeps its own block, whatever the slot is currently set
    # to, so these can be dialled in before switching the slot to them.
    # FX2 mirrors FX1 at +0x200.
    # Touch wah / auto wah (the FX-slot wahs, distinct from the pedal wah)
    T_WAH_MODE = "t_wah_mode"
    T_WAH_POLARITY = "t_wah_polarity"
    T_WAH_SENS = "t_wah_sens"
    T_WAH_FREQUENCY = "t_wah_frequency"
    T_WAH_PEAK = "t_wah_peak"
    T_WAH_DIRECT_MIX = "t_wah_direct_mix"
    T_WAH_LEVEL = "t_wah_level"

    AUTO_WAH_MODE = "auto_wah_mode"
    AUTO_WAH_FREQUENCY = "auto_wah_frequency"
    AUTO_WAH_PEAK = "auto_wah_peak"
    AUTO_WAH_RATE = "auto_wah_rate"
    AUTO_WAH_DEPTH = "auto_wah_depth"
    AUTO_WAH_DIRECT_MIX = "auto_wah_direct_mix"
    AUTO_WAH_LEVEL = "auto_wah_level"

    # Compressor
    COMP_TYPE = "comp_type"
    COMP_SUSTAIN = "comp_sustain"
    COMP_ATTACK = "comp_attack"
    COMP_TONE = "comp_tone"
    COMP_LEVEL = "comp_level"

    # Limiter
    LIMITER_TYPE = "limiter_type"
    LIMITER_ATTACK = "limiter_attack"
    LIMITER_THRESHOLD = "limiter_threshold"
    LIMITER_RATIO = "limiter_ratio"
    LIMITER_RELEASE = "limiter_release"
    LIMITER_LEVEL = "limiter_level"

    # Guitar simulator
    GUITAR_SIM_TYPE = "guitar_sim_type"
    GUITAR_SIM_LOW = "guitar_sim_low"
    GUITAR_SIM_HIGH = "guitar_sim_high"
    GUITAR_SIM_LEVEL = "guitar_sim_level"

    # Wave synth
    WAVE_SYNTH_WAVE = "wave_synth_wave"
    WAVE_SYNTH_CUTOFF = "wave_synth_cutoff"
    WAVE_SYNTH_RESONANCE = "wave_synth_resonance"
    WAVE_SYNTH_SENS = "wave_synth_sens"
    WAVE_SYNTH_DECAY = "wave_synth_decay"
    WAVE_SYNTH_DEPTH = "wave_synth_depth"
    WAVE_SYNTH_LEVEL = "wave_synth_level"

    # Octave
    OCTAVE_RANGE = "octave_range"
    OCTAVE_LEVEL = "octave_level"
    OCTAVE_DIRECT_MIX = "octave_direct_mix"

    PHASER_TYPE = "phaser_type"
    PHASER_RATE = "phaser_rate"
    PHASER_DEPTH = "phaser_depth"
    PHASER_MANUAL = "phaser_manual"
    PHASER_RESONANCE = "phaser_resonance"
    PHASER_STEP_RATE = "phaser_step_rate"
    PHASER_LEVEL = "phaser_level"
    PHASER_DIRECT_MIX = "phaser_direct_mix"

    FLANGER_RATE = "flanger_rate"
    FLANGER_DEPTH = "flanger_depth"
    FLANGER_MANUAL = "flanger_manual"
    FLANGER_RESONANCE = "flanger_resonance"
    FLANGER_LOW_CUT = "flanger_low_cut"
    FLANGER_LEVEL = "flanger_level"
    FLANGER_DIRECT_MIX = "flanger_direct_mix"

    ROTARY_RATE_FAST = "rotary_rate_fast"
    ROTARY_DEPTH = "rotary_depth"
    ROTARY_LEVEL = "rotary_level"

    SLICER_PATTERN = "slicer_pattern"
    SLICER_RATE = "slicer_rate"
    SLICER_TRIGGER_SENS = "slicer_trigger_sens"
    SLICER_LEVEL = "slicer_level"
    SLICER_DIRECT_MIX = "slicer_direct_mix"

    RING_MOD_MODE = "ring_mod_mode"
    RING_MOD_FREQUENCY = "ring_mod_frequency"
    RING_MOD_LEVEL = "ring_mod_level"
    RING_MOD_DIRECT_MIX = "ring_mod_direct_mix"

    HUMANIZER_MODE = "humanizer_mode"
    HUMANIZER_VOWEL1 = "humanizer_vowel1"
    HUMANIZER_VOWEL2 = "humanizer_vowel2"
    HUMANIZER_SENS = "humanizer_sens"
    HUMANIZER_RATE = "humanizer_rate"
    HUMANIZER_DEPTH = "humanizer_depth"
    HUMANIZER_MANUAL = "humanizer_manual"
    HUMANIZER_LEVEL = "humanizer_level"

    UNI_V_RATE = "uni_v_rate"
    UNI_V_DEPTH = "uni_v_depth"
    UNI_V_LEVEL = "uni_v_level"

    VIBRATO_RATE = "vibrato_rate"
    VIBRATO_DEPTH = "vibrato_depth"
    VIBRATO_LEVEL = "vibrato_level"

    TREMOLO_WAVESHAPE = "tremolo_waveshape"
    TREMOLO_RATE = "tremolo_rate"
    TREMOLO_DEPTH = "tremolo_depth"
    TREMOLO_LEVEL = "tremolo_level"

    # --- Channel / colour state --------------------------------------------
    # These store and read back, but writing them does NOT change the panel
    # LEDs or the sound on a MkII - tested on hardware. They appear to be a
    # status mirror the amp maintains, not a control. Kept because they are
    # useful to READ (they tell you which colour channel is selected).
    # Do not expect a write here to do anything audible or visible.
    LED_BOOST = "led_boost"
    LED_MOD = "led_mod"
    LED_FX = "led_fx"
    LED_DELAY = "led_delay"
    LED_REVERB = "led_reverb"

    # --- Noise suppressor --------------------------------------------------
    NOISE_SUPPRESSOR_SWITCH = "noise_suppressor_switch"
    NOISE_SUPPRESSOR_THRESHOLD = "noise_suppressor_threshold"
    NOISE_SUPPRESSOR_RELEASE = "noise_suppressor_release"

    # --- Reverb -----------------------------------------------------------
    REVERB_SWITCH = "reverb_switch"
    REVERB_TYPE = "reverb_type"
    REVERB_TIME = "reverb_time"
    REVERB_LEVEL = "reverb_level"
    REVERB_DIRECT_MIX = "reverb_direct_mix"

    # --- Pedal FX / wah ----------------------------------------------------
    # This is the real wah, on its own pedal section - not an FX slot.
    PEDAL_SWITCH = "pedal_switch"
    PEDAL_TYPE = "pedal_type"
    WAH_TYPE = "wah_type"
    WAH_POSITION = "wah_position"
    WAH_PEDAL_MIN = "wah_pedal_min"
    WAH_PEDAL_MAX = "wah_pedal_max"
    WAH_LEVEL = "wah_level"
    WAH_DIRECT_MIX = "wah_direct_mix"

    # --- Where it lives on the amp ----------------------------------------

    def address(self) -> int:
        """Its address in the amp's live area. Every one was verified by
        writing to the amp and reading the value back."""
        match self:
            case Param.AMP_TYPE:                   return 0x60000021
            case Param.GAIN:                       return 0x60000022
            case Param.KNOB_VOLUME:                return 0x60000023
            case Param.BASS:                       return 0x60000024
            case Param.MIDDLE:                     return 0x60000025
            case Param.TREBLE:                     return 0x60000026
            case Param.PRESENCE:                   return 0x60000027
            case Param.VOLUME:                     return 0x60000028
            case Param.BRIGHT:                     return 0x60000029
            case Param.BOOST_SWITCH:               return 0x60000010
            case Param.BOOST_TYPE:                 return 0x60000011
            case Param.BOOST_DRIVE:                return 0x60000012
            case Param.BOOST_BOTTOM:               return 0x60000013
            case Param.BOOST_TONE:                 return 0x60000014
            case Param.BOOST_SOLO_SWITCH:          return 0x60000015
            case Param.BOOST_SOLO_LEVEL:           return 0x60000016
            case Param.BOOST_LEVEL:                return 0x60000017
            case Param.BOOST_DIRECT_MIX:           return 0x60000018
            case Param.EQ_SWITCH:                  return 0x60000040
            case Param.EQ_TYPE:                    return 0x60000041
            case Param.FX1_SWITCH:                 return 0x60000100
            case Param.FX1_TYPE:                   return 0x60000101
            case Param.FX2_SWITCH:                 return 0x60000300
            case Param.FX2_TYPE:                   return 0x60000301
            case Param.DELAY_SWITCH:               return 0x60000500
            case Param.DELAY_TYPE:                 return 0x60000501
            case Param.DELAY_TIME:                 return 0x60000502
            case Param.DELAY_FEEDBACK:             return 0x60000504
            case Param.DELAY_HIGH_CUT:             return 0x60000505
            case Param.DELAY_LEVEL:                return 0x60000506
            case Param.DELAY_DIRECT_MIX:           return 0x60000507
            case Param.DELAY2_SWITCH:              return 0x60000520
            case Param.DELAY2_TYPE:                return 0x60000521
            case Param.DELAY2_TIME:                return 0x60000522
            case Param.DELAY2_FEEDBACK:            return 0x60000524
            case Param.DELAY2_HIGH_CUT:            return 0x60000525
            case Param.DELAY2_LEVEL:               return 0x60000526
            case Param.DELAY2_DIRECT_MIX:          return 0x60000527
            case Param.EQ_BAND_31HZ:               return 0x6000004D
            case Param.EQ_BAND_62HZ:               return 0x6000004E
            case Param.EQ_BAND_125HZ:              return 0x6000004F
            case Param.EQ_BAND_250HZ:              return 0x60000050
            case Param.EQ_BAND_500HZ:              return 0x60000051
            case Param.EQ_BAND_1KHZ:               return 0x60000052
            case Param.EQ_BAND_2KHZ:               return 0x60000053
            case Param.EQ_BAND_4KHZ:               return 0x60000054
            case Param.EQ_BAND_8KHZ:               return 0x60000055
            case Param.EQ_BAND_16KHZ:              return 0x60000056
            case Param.EQ_LEVEL:                   return 0x60000057
            case Param.T_WAH_MODE:                 return 0x60000102
            case Param.T_WAH_POLARITY:             return 0x60000103
            case Param.T_WAH_SENS:                 return 0x60000104
            case Param.T_WAH_FREQUENCY:            return 0x60000105
            case Param.T_WAH_PEAK:                 return 0x60000106
            case Param.T_WAH_DIRECT_MIX:           return 0x60000107
            case Param.T_WAH_LEVEL:                return 0x60000108
            case Param.AUTO_WAH_MODE:              return 0x60000109
            case Param.AUTO_WAH_FREQUENCY:         return 0x6000010A
            case Param.AUTO_WAH_PEAK:              return 0x6000010B
            case Param.AUTO_WAH_RATE:              return 0x6000010C
            case Param.AUTO_WAH_DEPTH:             return 0x6000010D
            case Param.AUTO_WAH_DIRECT_MIX:        return 0x6000010E
            case Param.AUTO_WAH_LEVEL:             return 0x6000010F
            case Param.COMP_TYPE:                  return 0x60000116
            case Param.COMP_SUSTAIN:               return 0x60000117
            case Param.COMP_ATTACK:                return 0x60000118
            case Param.COMP_TONE:                  return 0x60000119
            case Param.COMP_LEVEL:                 return 0x6000011A
            case Param.LIMITER_TYPE:               return 0x6000011B
            case Param.LIMITER_ATTACK:             return 0x6000011C
            case Param.LIMITER_THRESHOLD:          return 0x6000011D
            case Param.LIMITER_RATIO:              return 0x6000011E
            case Param.LIMITER_RELEASE:            return 0x6000011F
            case Param.LIMITER_LEVEL:              return 0x60000120
            case Param.GUITAR_SIM_TYPE:            return 0x60000137
            case Param.GUITAR_SIM_LOW:             return 0x60000138
            case Param.GUITAR_SIM_HIGH:            return 0x60000139
            case Param.GUITAR_SIM_LEVEL:           return 0x6000013A
            case Param.WAVE_SYNTH_WAVE:            return 0x6000013F
            case Param.WAVE_SYNTH_CUTOFF:          return 0x60000140
            case Param.WAVE_SYNTH_RESONANCE:       return 0x60000141
            case Param.WAVE_SYNTH_SENS:            return 0x60000142
            case Param.WAVE_SYNTH_DECAY:           return 0x60000143
            case Param.WAVE_SYNTH_DEPTH:           return 0x60000144
            case Param.WAVE_SYNTH_LEVEL:           return 0x60000145
            case Param.OCTAVE_RANGE:               return 0x60000147
            case Param.OCTAVE_LEVEL:               return 0x60000148
            case Param.OCTAVE_DIRECT_MIX:          return 0x60000149
            case Param.PHASER_TYPE:                return 0x60000203
            case Param.PHASER_RATE:                return 0x60000204
            case Param.PHASER_DEPTH:               return 0x60000205
            case Param.PHASER_MANUAL:              return 0x60000206
            case Param.PHASER_RESONANCE:           return 0x60000207
            case Param.PHASER_STEP_RATE:           return 0x60000208
            case Param.PHASER_LEVEL:               return 0x60000209
            case Param.PHASER_DIRECT_MIX:          return 0x6000020A
            case Param.FLANGER_RATE:               return 0x6000020B
            case Param.FLANGER_DEPTH:              return 0x6000020C
            case Param.FLANGER_MANUAL:             return 0x6000020D
            case Param.FLANGER_RESONANCE:          return 0x6000020E
            case Param.FLANGER_LOW_CUT:            return 0x60000210
            case Param.FLANGER_LEVEL:              return 0x60000211
            case Param.FLANGER_DIRECT_MIX:         return 0x60000212
            case Param.ROTARY_RATE_FAST:           return 0x60000219
            case Param.ROTARY_DEPTH:               return 0x6000021C
            case Param.ROTARY_LEVEL:               return 0x6000021D
            case Param.SLICER_PATTERN:             return 0x60000221
            case Param.SLICER_RATE:                return 0x60000222
            case Param.SLICER_TRIGGER_SENS:        return 0x60000223
            case Param.SLICER_LEVEL:               return 0x60000224
            case Param.SLICER_DIRECT_MIX:          return 0x60000225
            case Param.RING_MOD_MODE:              return 0x6000022B
            case Param.RING_MOD_FREQUENCY:         return 0x6000022C
            case Param.RING_MOD_LEVEL:             return 0x6000022D
            case Param.RING_MOD_DIRECT_MIX:        return 0x6000022E
            case Param.HUMANIZER_MODE:             return 0x6000022F
            case Param.HUMANIZER_VOWEL1:           return 0x60000230
            case Param.HUMANIZER_VOWEL2:           return 0x60000231
            case Param.HUMANIZER_SENS:             return 0x60000232
            case Param.HUMANIZER_RATE:             return 0x60000233
            case Param.HUMANIZER_DEPTH:            return 0x60000234
            case Param.HUMANIZER_MANUAL:           return 0x60000235
            case Param.HUMANIZER_LEVEL:            return 0x60000236
            case Param.UNI_V_RATE:                 return 0x6000021E
            case Param.UNI_V_DEPTH:                return 0x6000021F
            case Param.UNI_V_LEVEL:                return 0x60000220
            case Param.VIBRATO_RATE:               return 0x60000226
            case Param.VIBRATO_DEPTH:              return 0x60000227
            case Param.VIBRATO_LEVEL:              return 0x6000022A
            case Param.TREMOLO_WAVESHAPE:          return 0x60000213
            case Param.TREMOLO_RATE:               return 0x60000214
            case Param.TREMOLO_DEPTH:              return 0x60000215
            case Param.TREMOLO_LEVEL:              return 0x60000216
            case Param.LED_BOOST:                  return 0x6000065D
            case Param.LED_MOD:                    return 0x6000065E
            case Param.LED_FX:                     return 0x6000065F
            case Param.LED_DELAY:                  return 0x60000660
            case Param.LED_REVERB:                 return 0x60000661
            case Param.NOISE_SUPPRESSOR_SWITCH:    return 0x60000566
            case Param.NOISE_SUPPRESSOR_THRESHOLD: return 0x60000567
            case Param.NOISE_SUPPRESSOR_RELEASE:   return 0x60000568
            case Param.REVERB_SWITCH:              return 0x60000540
            case Param.REVERB_TYPE:                return 0x60000541
            case Param.REVERB_TIME:                return 0x60000542
            case Param.REVERB_LEVEL:               return 0x60000548
            case Param.REVERB_DIRECT_MIX:          return 0x60000549
            case Param.PEDAL_SWITCH:               return 0x60000550
            case Param.PEDAL_TYPE:                 return 0x60000551
            case Param.WAH_TYPE:                   return 0x60000552
            case Param.WAH_POSITION:               return 0x60000553
            case Param.WAH_PEDAL_MIN:              return 0x60000554
            case Param.WAH_PEDAL_MAX:              return 0x60000555
            case Param.WAH_LEVEL:                  return 0x60000556
            case Param.WAH_DIRECT_MIX:             return 0x60000557

    def size(self) -> int:
        """Bytes the amp stores it in. Two bytes are 7-bit halves."""
        return 2 if self in (Param.DELAY_TIME, Param.DELAY2_TIME) else 1

    def offset(self) -> int:
        """What the amp adds before storing it: EQ bands are stored 0-48."""
        return 24 if self.is_eq_band() else 0

    # --- What sort of control it is ---------------------------------------

    def kind(self) -> Kind:
        match self:
            case _ if self.options() is not None:  return Kind.ENUM
            case _ if self.value.endswith("_switch"):  return Kind.TOGGLE
            case (
                Param.BRIGHT | Param.EQ_TYPE | Param.T_WAH_MODE | Param.T_WAH_POLARITY |
                Param.AUTO_WAH_MODE | Param.WAVE_SYNTH_WAVE | Param.RING_MOD_MODE |
                Param.HUMANIZER_MODE
            ):
                return Kind.TOGGLE
            case _:
                return Kind.RANGE

    def range(self) -> tuple[int, int]:
        """(lowest, highest), in real units."""
        match self:
            case Param.BOOST_TYPE:                          return (0, 25)
            case Param.FX1_TYPE | Param.FX2_TYPE:           return (0, 40)
            case Param.DELAY_TYPE | Param.DELAY2_TYPE:      return (0, 10)
            case _ if self.kind() is Kind.ENUM:             return (0, max(self.options()))
            case _ if self.kind() is Kind.TOGGLE:           return (0, 1)
            case _ if self.is_eq_band():                    return (-24, 24)
            case Param.DELAY_TIME | Param.DELAY2_TIME:      return (1, 2000)
            case Param.DELAY_LEVEL | Param.DELAY2_LEVEL:    return (0, 120)
            case Param.DELAY_HIGH_CUT | Param.DELAY2_HIGH_CUT:  return (0, 14)
            case Param.EQ_LEVEL:                            return (0, 48)
            case Param.REVERB_TIME:                         return (0, 99)
            case Param.SLICER_PATTERN:                      return (0, 19)
            case Param.LIMITER_RATIO:                       return (0, 17)
            case Param.FLANGER_LOW_CUT:                     return (0, 10)
            case Param.GUITAR_SIM_TYPE:                     return (0, 7)
            case Param.COMP_TYPE:                           return (0, 6)
            case Param.HUMANIZER_VOWEL1 | Param.HUMANIZER_VOWEL2:  return (0, 4)
            case Param.OCTAVE_RANGE | Param.PHASER_TYPE:    return (0, 3)
            case Param.LIMITER_TYPE:                        return (0, 2)
            case _:                                         return (0, 100)

    def unit(self) -> str | None:
        match self:
            case Param.DELAY_TIME | Param.DELAY2_TIME:  return "ms"
            case _ if self.is_eq_band():                return "dB"
            case _:                                     return None

    def is_writable(self) -> bool:
        """False for the settings the amp reports but ignores writes to."""
        return self is not Param.KNOB_VOLUME and not self.value.startswith("led_")

    def options(self) -> dict[int, str] | None:
        """The named values of a setting that is one of a set."""
        match self:
            case Param.AMP_TYPE:
                # The preamp models. The front-panel knob selects five of these; the
                # rest ("sneaky amps") are reachable only over MIDI.
                return {
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
            case Param.BOOST_TYPE:
                return {
                    0x00: "Mid Boost", 0x01: "Clean Boost", 0x02: "Treble Boost",
                    0x03: "Crunch OD", 0x04: "Natural OD", 0x05: "Warm OD",
                    0x06: "Fat DS", 0x08: "Metal DS", 0x09: "Oct Fuzz",
                    0x0A: "Blues Drive", 0x0B: "Overdrive", 0x0C: "T-Scream",
                    0x0D: "Turbo OD", 0x0E: "Distortion", 0x0F: "Rat",
                    0x10: "Guv DS", 0x11: "DST+", 0x12: "Metal Zone",
                    0x13: "'60s Fuzz", 0x14: "Muff Fuzz",
                }
            case Param.FX1_TYPE | Param.FX2_TYPE:
                # Effect types for the FX1/FX2 slots. Pedal Wah (2) is the one that
                # responds to a treadle position; T Wah and Auto Wah move on their own.
                return {
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
            case Param.DELAY_TYPE | Param.DELAY2_TYPE:
                # Delay types. The amp accepts 0-10 but reports only numbers, and no
                # MkII source lists the names, so these come from the first-generation
                # docs and are the least certain table here. Check against BOSS Tone
                # Studio if a name looks wrong; the numbers themselves are correct.
                return {
                    0x00: "Digital",
                    0x06: "Reverse",
                    0x07: "Analog",
                    0x08: "Tape Echo",
                    0x09: "Modulate",
                }
            case _ if self.value.startswith("led_"):
                # Channel colours as reported by the led_* parameters. The numbers are what
                # the amp reports; the colour names are the documented convention and are
                # unconfirmed by eye. Writing these does not move the panel LEDs.
                return {0x00: "off", 0x01: "green", 0x02: "red", 0x03: "yellow"}
            case Param.REVERB_TYPE:
                # Reverb types, also from the first-generation docs - numbers verified,
                # names unconfirmed on the MkII.
                return {
                    0x00: "Room", 0x01: "Hall", 0x02: "Plate",
                    0x03: "Spring", 0x04: "Modulate", 0x05: "Reverb+Delay", 0x06: "Fast Decay",
                }
            case Param.PEDAL_TYPE:
                # What the expression pedal section is doing, for pedal_type.
                return {0x00: "Wah", 0x01: "Pedal Bend", 0x02: "Wah 95E"}
            case Param.WAH_TYPE:
                # The pedal wah voicings, for wah_type.
                return {
                    0x00: "Cry Wah",
                    0x01: "Vo Wah",
                    0x02: "Fat Wah",
                    0x03: "Light Wah",
                    0x04: "7String Wah",
                    0x05: "Reso Wah",
                }
            case _:
                return None

    def group(self) -> str:
        """The UI section this setting belongs to."""
        match self:
            case _ if self.value.startswith("eq_"):               return "eq"
            case _ if self.value.startswith("boost_"):            return "boost"
            case _ if self.value.startswith("delay2_"):           return "delay2"
            case _ if self.value.startswith("delay_"):            return "delay"
            case _ if self.value.startswith("reverb_"):           return "reverb"
            case _ if self.value.startswith(("wah_", "pedal_")):  return "wah"
            case _ if self.value.startswith("fx1_"):              return "fx1"
            case _ if self.value.startswith("fx2_"):              return "fx2"
            case _ if self.value.startswith("noise_suppressor_"): return "noise_gate"
            case _ if self.value.startswith("led_"):              return "channels"
            case _ if self.value.startswith((
                "t_wah_", "auto_wah_", "comp_", "limiter_", "guitar_sim_",
                "wave_synth_", "octave_", "phaser_", "flanger_", "tremolo_",
                "vibrato_", "uni_v_", "rotary_", "slicer_", "ring_mod_", "humanizer_",
            )):
                return "effects"
            case _:
                return "amp"

    # --- Bytes -------------------------------------------------------------

    def decode(self, data: list[int]) -> int:
        """The value in real units, from the amp's bytes."""
        stored = data[0] * 128 + data[1] if self.size() == 2 else data[0]
        return stored - self.offset()

    def encode(self, value: int) -> list[int]:
        """The bytes the amp stores for `value` in real units."""
        stored = value + self.offset()
        return [stored // 128, stored % 128] if self.size() == 2 else [stored]

    def describe(self) -> dict:
        """This setting as a JSON-ready dict, for the UI."""
        low, high = self.range()
        options = self.options()
        entry = {
            "name": self.value,
            "group": self.group(),
            "kind": self.kind().value,
            "min": low,
            "max": high,
            "writable": self.is_writable(),
            "unit": self.unit(),
            "options": {str(number): label for number, label in options.items()} if options else None,
        }
        return {key: value for key, value in entry.items() if value is not None}

    # --- Helpers -----------------------------------------------------------

    def is_eq_band(self) -> bool:
        return self.value.startswith("eq_band_")

    @classmethod
    def eq_bands(cls) -> list["Param"]:
        """The ten graphic EQ bands, low to high."""
        return [param for param in cls if param.is_eq_band()]

    @classmethod
    def schema(cls) -> list[dict]:
        """Every setting, described for the UI, sorted by name."""
        return [param.describe() for param in sorted(cls)]
