"""Every setting the Katana MkII exposes, as an enum.

    from katana_amp.param import Param

    Param("gain")                    Param.GAIN       (like Param::from('gain'))
    Param.GAIN.value                 "gain"
    Param.GAIN.address()             0x60000022
    Param.GAIN.kind()                Kind.RANGE
    Param.GAIN.range()               (0, 120)
    Param.AMP_TYPE.options()[8]      "JC-120"
    Param.FX2_PHASER_RATE.address()  0x60000404   (effect knobs exist once per slot)
    Param.schema()                   every setting, for the UI

The addresses are the MkII's live area at 0x60000000 (see katana.py). The
source for all of them is Roland's own address map, shipped inside BOSS
Tone Studio (js/config/address_map.js) - ranges, offsets and names here
match what Tone Studio shows. The FX-slot effects are a table of their own,
in effects.py.
"""

from enum import StrEnum

from katana_amp.effects import EFFECTS, HIGH_CUT, LOW_CUT, FREQUENCY, Q, SLOT_BASE
from katana_amp.kind import Kind

# Settings that copy another setting's layout: (prefix, twin prefix, how
# far away it lives). delay2_feedback is delay_feedback 0x20 on; the global
# EQ is the main EQ moved into the system area (its switch, type and
# position sit differently, so address() lists those three itself).
TWINS = (
    ("delay2_", "delay_", 0x20),
    ("eq2_", "eq_", 0x20),
    ("global_eq_", "eq_", 0x00000013 - 0x60000042),
)
# Same prefix, but a setting of their own rather than a copy.
NOT_TWINS = ("eq2_position", "global_eq_position", "global_eq_select")

# The colour-channel blocks, in the order the amp stores them.
COLOUR_BLOCKS = ("boost", "mod", "fx", "delay", "reverb", "delay2")
COLOURS = ("green", "red", "yellow")
COLOUR_BASE = 0x60000624


class Param(StrEnum):
    # Names used only while the class body runs (the effect loop at the end).
    # Enum deletes these from the class afterwards, so none may clash with a
    # method name.
    _ignore_ = "members slot fx_effect fx_knob colour_block colour"

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
    # What the panel's TYPE knob and VARIATION button are set to. The amp
    # turns these two into amp_type; Tone Studio shows them, never amp_type.
    PANEL_AMP_TYPE = "panel_amp_type"
    VARIATION = "variation"
    CABINET_RESONANCE = "cabinet_resonance"
    # The MkII's SOLO (a level boost for leads), separate from the boost's own.
    SOLO_SWITCH = "solo_switch"
    SOLO_LEVEL = "solo_level"
    # CONTOUR: three stored voicings; contour_select picks which is active.
    CONTOUR_SWITCH = "contour_switch"
    CONTOUR_SELECT = "contour_select"
    CONTOUR1_TYPE = "contour1_type"
    CONTOUR1_FREQ_SHIFT = "contour1_freq_shift"
    CONTOUR2_TYPE = "contour2_type"
    CONTOUR2_FREQ_SHIFT = "contour2_freq_shift"
    CONTOUR3_TYPE = "contour3_type"
    CONTOUR3_FREQ_SHIFT = "contour3_freq_shift"

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
    # One EQ block, two types: eq_type picks parametric or the 10-band GE-10.
    EQ_SWITCH = "eq_switch"
    EQ_TYPE = "eq_type"
    EQ_POSITION = "eq_position"
    EQ_LOW_CUT = "eq_low_cut"
    EQ_LOW_GAIN = "eq_low_gain"
    EQ_LOW_MID_FREQ = "eq_low_mid_freq"
    EQ_LOW_MID_Q = "eq_low_mid_q"
    EQ_LOW_MID_GAIN = "eq_low_mid_gain"
    EQ_HIGH_MID_FREQ = "eq_high_mid_freq"
    EQ_HIGH_MID_Q = "eq_high_mid_q"
    EQ_HIGH_MID_GAIN = "eq_high_mid_gain"
    EQ_HIGH_GAIN = "eq_high_gain"
    EQ_HIGH_CUT = "eq_high_cut"
    EQ_PEQ_LEVEL = "eq_peq_level"
    # Graphic EQ: stored 0-48, where 24 is flat; offset 24 makes it -24..+24 dB.
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

    # --- Effect slots ------------------------------------------------------
    # MOD is slot 1, FX is slot 2. Their effects' knobs are generated at the
    # bottom of this class, from effects.py.
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
    DELAY_TAP_TIME = "delay_tap_time"          # Pan: where the echo sits, L->R
    DELAY_MOD_RATE = "delay_mod_rate"          # Modulate
    DELAY_MOD_DEPTH = "delay_mod_depth"
    DELAY_SDE_RANGE = "delay_sde_range"        # SDE-3000
    DELAY_SDE_FILTER = "delay_sde_filter"
    DELAY_SDE_FEEDBACK_PHASE = "delay_sde_feedback_phase"
    DELAY_SDE_DELAY_PHASE = "delay_sde_delay_phase"
    DELAY_SDE_MOD_SWITCH = "delay_sde_mod_switch"

    # --- Delay 2 (a second, independent delay engine) ---------------------
    DELAY2_SWITCH = "delay2_switch"
    DELAY2_TYPE = "delay2_type"
    DELAY2_TIME = "delay2_time"
    DELAY2_FEEDBACK = "delay2_feedback"
    DELAY2_HIGH_CUT = "delay2_high_cut"
    DELAY2_LEVEL = "delay2_level"
    DELAY2_DIRECT_MIX = "delay2_direct_mix"
    DELAY2_TAP_TIME = "delay2_tap_time"
    DELAY2_MOD_RATE = "delay2_mod_rate"
    DELAY2_MOD_DEPTH = "delay2_mod_depth"
    DELAY2_SDE_RANGE = "delay2_sde_range"
    DELAY2_SDE_FILTER = "delay2_sde_filter"
    DELAY2_SDE_FEEDBACK_PHASE = "delay2_sde_feedback_phase"
    DELAY2_SDE_DELAY_PHASE = "delay2_sde_delay_phase"
    DELAY2_SDE_MOD_SWITCH = "delay2_sde_mod_switch"

    # --- Reverb -----------------------------------------------------------
    REVERB_SWITCH = "reverb_switch"
    REVERB_TYPE = "reverb_type"
    REVERB_TIME = "reverb_time"
    REVERB_PRE_DELAY = "reverb_pre_delay"
    REVERB_LOW_CUT = "reverb_low_cut"
    REVERB_HIGH_CUT = "reverb_high_cut"
    REVERB_DENSITY = "reverb_density"
    REVERB_LEVEL = "reverb_level"
    REVERB_DIRECT_MIX = "reverb_direct_mix"
    REVERB_SPRING_COLOR = "reverb_spring_color"

    # --- Pedal FX ------------------------------------------------------------
    # Its own section on the expression pedal, not an FX slot. pedal_type
    # picks one of three, and each keeps its own settings.
    PEDAL_SWITCH = "pedal_switch"
    PEDAL_TYPE = "pedal_type"
    PEDAL_POSITION = "pedal_position"          # before the amp, or after it
    WAH_TYPE = "wah_type"
    WAH_POSITION = "wah_position"
    WAH_PEDAL_MIN = "wah_pedal_min"
    WAH_PEDAL_MAX = "wah_pedal_max"
    WAH_LEVEL = "wah_level"
    WAH_DIRECT_MIX = "wah_direct_mix"
    PEDAL_BEND_PITCH = "pedal_bend_pitch"
    PEDAL_BEND_POSITION = "pedal_bend_position"
    PEDAL_BEND_LEVEL = "pedal_bend_level"
    PEDAL_BEND_DIRECT_MIX = "pedal_bend_direct_mix"
    WAH_95E_POSITION = "wah_95e_position"
    WAH_95E_PEDAL_MIN = "wah_95e_pedal_min"
    WAH_95E_PEDAL_MAX = "wah_95e_pedal_max"
    WAH_95E_LEVEL = "wah_95e_level"
    WAH_95E_DIRECT_MIX = "wah_95e_direct_mix"
    FOOT_VOLUME = "foot_volume"

    # --- Effects loop (SEND/RETURN jacks) ----------------------------------
    SEND_RETURN_SWITCH = "send_return_switch"
    SEND_RETURN_MODE = "send_return_mode"
    SEND_RETURN_POSITION = "send_return_position"
    SEND_RETURN_SEND_LEVEL = "send_return_send_level"
    SEND_RETURN_RETURN_LEVEL = "send_return_return_level"

    # --- Noise suppressor --------------------------------------------------
    NOISE_SUPPRESSOR_SWITCH = "noise_suppressor_switch"
    NOISE_SUPPRESSOR_THRESHOLD = "noise_suppressor_threshold"
    NOISE_SUPPRESSOR_RELEASE = "noise_suppressor_release"

    # The key the Harmonist harmonises in (both slots share it).
    MASTER_KEY = "master_key"

    # --- Second EQ (EQ2) ---------------------------------------------------
    # A whole second EQ, same layout as the first, 0x20 further on. Only its
    # position lives elsewhere. Ranges etc. come from the eq_ twin.
    EQ2_SWITCH = "eq2_switch"
    EQ2_TYPE = "eq2_type"
    EQ2_POSITION = "eq2_position"
    EQ2_LOW_CUT = "eq2_low_cut"
    EQ2_LOW_GAIN = "eq2_low_gain"
    EQ2_LOW_MID_FREQ = "eq2_low_mid_freq"
    EQ2_LOW_MID_Q = "eq2_low_mid_q"
    EQ2_LOW_MID_GAIN = "eq2_low_mid_gain"
    EQ2_HIGH_MID_FREQ = "eq2_high_mid_freq"
    EQ2_HIGH_MID_Q = "eq2_high_mid_q"
    EQ2_HIGH_MID_GAIN = "eq2_high_mid_gain"
    EQ2_HIGH_GAIN = "eq2_high_gain"
    EQ2_HIGH_CUT = "eq2_high_cut"
    EQ2_PEQ_LEVEL = "eq2_peq_level"
    EQ2_BAND_31HZ = "eq2_band_31hz"
    EQ2_BAND_62HZ = "eq2_band_62hz"
    EQ2_BAND_125HZ = "eq2_band_125hz"
    EQ2_BAND_250HZ = "eq2_band_250hz"
    EQ2_BAND_500HZ = "eq2_band_500hz"
    EQ2_BAND_1KHZ = "eq2_band_1khz"
    EQ2_BAND_2KHZ = "eq2_band_2khz"
    EQ2_BAND_4KHZ = "eq2_band_4khz"
    EQ2_BAND_8KHZ = "eq2_band_8khz"
    EQ2_BAND_16KHZ = "eq2_band_16khz"
    EQ2_LEVEL = "eq2_level"

    # --- Solo EQ / solo delay ----------------------------------------------
    # Extra EQ and delay that come in with SOLO. (The solo EQ's position is
    # left out: Tone Studio shows its two values as icons, with no names.)
    SOLO_EQ_SWITCH = "solo_eq_switch"
    SOLO_EQ_LOW_CUT = "solo_eq_low_cut"
    SOLO_EQ_LOW_GAIN = "solo_eq_low_gain"
    SOLO_EQ_MID_FREQ = "solo_eq_mid_freq"
    SOLO_EQ_MID_Q = "solo_eq_mid_q"
    SOLO_EQ_MID_GAIN = "solo_eq_mid_gain"
    SOLO_EQ_HIGH_GAIN = "solo_eq_high_gain"
    SOLO_EQ_HIGH_CUT = "solo_eq_high_cut"
    SOLO_EQ_LEVEL = "solo_eq_level"
    SOLO_DELAY_SWITCH = "solo_delay_switch"
    SOLO_DELAY_CARRYOVER = "solo_delay_carryover"   # let echoes ring on after solo is switched off
    SOLO_DELAY_TIME = "solo_delay_time"
    SOLO_DELAY_FEEDBACK = "solo_delay_feedback"
    SOLO_DELAY_LEVEL = "solo_delay_level"
    SOLO_DELAY_DIRECT_MIX = "solo_delay_direct_mix"
    SOLO_DELAY_FILTER = "solo_delay_filter"
    SOLO_DELAY_HIGH_CUT = "solo_delay_high_cut"
    SOLO_DELAY_MOD_SWITCH = "solo_delay_mod_switch"
    SOLO_DELAY_MOD_RATE = "solo_delay_mod_rate"
    SOLO_DELAY_MOD_DEPTH = "solo_delay_mod_depth"

    # --- Amp-wide (system) settings ----------------------------------------
    # Not part of any channel: these apply to every channel and survive
    # switching. They live in a separate area from 0x00000000. The USB audio
    # settings there are deliberately absent - the Pi's tuner, recorder and
    # backing tracks depend on them.
    GLOBAL_EQ_SWITCH = "global_eq_switch"
    GLOBAL_EQ_TYPE = "global_eq_type"
    GLOBAL_EQ_POSITION = "global_eq_position"
    GLOBAL_EQ_LOW_CUT = "global_eq_low_cut"
    GLOBAL_EQ_LOW_GAIN = "global_eq_low_gain"
    GLOBAL_EQ_LOW_MID_FREQ = "global_eq_low_mid_freq"
    GLOBAL_EQ_LOW_MID_Q = "global_eq_low_mid_q"
    GLOBAL_EQ_LOW_MID_GAIN = "global_eq_low_mid_gain"
    GLOBAL_EQ_HIGH_MID_FREQ = "global_eq_high_mid_freq"
    GLOBAL_EQ_HIGH_MID_Q = "global_eq_high_mid_q"
    GLOBAL_EQ_HIGH_MID_GAIN = "global_eq_high_mid_gain"
    GLOBAL_EQ_HIGH_GAIN = "global_eq_high_gain"
    GLOBAL_EQ_HIGH_CUT = "global_eq_high_cut"
    GLOBAL_EQ_PEQ_LEVEL = "global_eq_peq_level"
    GLOBAL_EQ_BAND_31HZ = "global_eq_band_31hz"
    GLOBAL_EQ_BAND_62HZ = "global_eq_band_62hz"
    GLOBAL_EQ_BAND_125HZ = "global_eq_band_125hz"
    GLOBAL_EQ_BAND_250HZ = "global_eq_band_250hz"
    GLOBAL_EQ_BAND_500HZ = "global_eq_band_500hz"
    GLOBAL_EQ_BAND_1KHZ = "global_eq_band_1khz"
    GLOBAL_EQ_BAND_2KHZ = "global_eq_band_2khz"
    GLOBAL_EQ_BAND_4KHZ = "global_eq_band_4khz"
    GLOBAL_EQ_BAND_8KHZ = "global_eq_band_8khz"
    GLOBAL_EQ_BAND_16KHZ = "global_eq_band_16khz"
    GLOBAL_EQ_LEVEL = "global_eq_level"
    GLOBAL_EQ_SELECT = "global_eq_select"           # which of three stored global EQs is loaded
    LINE_OUT_AIR_FEEL = "line_out_air_feel"
    STEREO_EXPAND = "stereo_expand"
    LINE_OUT_CUSTOM_SWITCH = "line_out_custom_switch"
    LINE_OUT_CUSTOM_SELECT = "line_out_custom_select"
    LINE_OUT_CUSTOM1_MIC_TYPE = "line_out_custom1_mic_type"
    LINE_OUT_CUSTOM1_MIC_DISTANCE = "line_out_custom1_mic_distance"
    LINE_OUT_CUSTOM1_MIC_POSITION = "line_out_custom1_mic_position"
    LINE_OUT_CUSTOM2_MIC_TYPE = "line_out_custom2_mic_type"
    LINE_OUT_CUSTOM2_MIC_DISTANCE = "line_out_custom2_mic_distance"
    LINE_OUT_CUSTOM2_MIC_POSITION = "line_out_custom2_mic_position"

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

    # --- Per-effect knobs, one set per FX slot -------------------------------
    # FX1_PHASER_RATE = "fx1_phaser_rate", FX2_PHASER_RATE = ..., for every
    # knob in effects.py. vars() is the class body's namespace, so writing to
    # it declares a member, exactly as a line like the ones above would.
    members = vars()
    for slot in SLOT_BASE:
        for fx_effect in EFFECTS:
            for fx_knob in fx_effect.knobs:
                members[f"FX{slot}_{fx_effect.key}_{fx_knob.key}".upper()] = f"fx{slot}_{fx_effect.key}_{fx_knob.key}"

    # --- Colour channels -----------------------------------------------------
    # Each block's panel button cycles green/red/yellow, and each colour
    # holds its own effect type: COLOR_MOD_RED = which effect MOD's red is.
    # COLOR_SELECT_MOD = which colour MOD is on now (writing it switches).
    # COLOR_LAYER_* = what the delay/reverb knob does on each colour.
    for colour_block in COLOUR_BLOCKS:
        for colour in COLOURS:
            members[f"COLOR_{colour_block}_{colour}".upper()] = f"color_{colour_block}_{colour}"
    for colour in COLOURS:
        members[f"COLOR_LAYER_{colour}".upper()] = f"color_layer_{colour}"
    for colour_block in COLOUR_BLOCKS[:5]:
        members[f"COLOR_SELECT_{colour_block}".upper()] = f"color_select_{colour_block}"

    # --- Where it lives on the amp ----------------------------------------

    def address(self) -> int:
        """Its address in the amp's live area."""
        if self in EFFECT_KNOBS:
            slot, _, knob = EFFECT_KNOBS[self]
            # The slot bases end in 00, so adding never carries past 0x7F.
            return SLOT_BASE[slot] + knob.offset
        if self in COLOUR_SETTINGS:
            return COLOUR_SETTINGS[self][0]
        match self:
            case Param.BOOST_SWITCH:               return 0x60000010
            case Param.BOOST_TYPE:                 return 0x60000011
            case Param.BOOST_DRIVE:                return 0x60000012
            case Param.BOOST_BOTTOM:               return 0x60000013
            case Param.BOOST_TONE:                 return 0x60000014
            case Param.BOOST_SOLO_SWITCH:          return 0x60000015
            case Param.BOOST_SOLO_LEVEL:           return 0x60000016
            case Param.BOOST_LEVEL:                return 0x60000017
            case Param.BOOST_DIRECT_MIX:           return 0x60000018
            case Param.AMP_TYPE:                   return 0x60000021
            case Param.GAIN:                       return 0x60000022
            case Param.KNOB_VOLUME:                return 0x60000023
            case Param.BASS:                       return 0x60000024
            case Param.MIDDLE:                     return 0x60000025
            case Param.TREBLE:                     return 0x60000026
            case Param.PRESENCE:                   return 0x60000027
            case Param.VOLUME:                     return 0x60000028
            case Param.BRIGHT:                     return 0x60000029
            case Param.EQ_SWITCH:                  return 0x60000040
            case Param.EQ_TYPE:                    return 0x60000041
            case Param.EQ_LOW_CUT:                 return 0x60000042
            case Param.EQ_LOW_GAIN:                return 0x60000043
            case Param.EQ_LOW_MID_FREQ:            return 0x60000044
            case Param.EQ_LOW_MID_Q:               return 0x60000045
            case Param.EQ_LOW_MID_GAIN:            return 0x60000046
            case Param.EQ_HIGH_MID_FREQ:           return 0x60000047
            case Param.EQ_HIGH_MID_Q:              return 0x60000048
            case Param.EQ_HIGH_MID_GAIN:           return 0x60000049
            case Param.EQ_HIGH_GAIN:               return 0x6000004A
            case Param.EQ_HIGH_CUT:                return 0x6000004B
            case Param.EQ_PEQ_LEVEL:               return 0x6000004C
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
            case Param.DELAY_TAP_TIME:             return 0x60000508
            case Param.DELAY_MOD_RATE:             return 0x60000513
            case Param.DELAY_MOD_DEPTH:            return 0x60000514
            case Param.DELAY_SDE_RANGE:            return 0x60000515
            case Param.DELAY_SDE_FILTER:           return 0x60000516
            case Param.DELAY_SDE_FEEDBACK_PHASE:   return 0x60000517
            case Param.DELAY_SDE_DELAY_PHASE:      return 0x60000518
            case Param.DELAY_SDE_MOD_SWITCH:       return 0x60000519
            case Param.REVERB_SWITCH:              return 0x60000540
            case Param.REVERB_TYPE:                return 0x60000541
            case Param.REVERB_TIME:                return 0x60000542
            case Param.REVERB_PRE_DELAY:           return 0x60000543
            case Param.REVERB_LOW_CUT:             return 0x60000545
            case Param.REVERB_HIGH_CUT:            return 0x60000546
            case Param.REVERB_DENSITY:             return 0x60000547
            case Param.REVERB_LEVEL:               return 0x60000548
            case Param.REVERB_DIRECT_MIX:          return 0x60000549
            case Param.REVERB_SPRING_COLOR:        return 0x6000054B
            case Param.PEDAL_SWITCH:               return 0x60000550
            case Param.PEDAL_TYPE:                 return 0x60000551
            case Param.WAH_TYPE:                   return 0x60000552
            case Param.WAH_POSITION:               return 0x60000553
            case Param.WAH_PEDAL_MIN:              return 0x60000554
            case Param.WAH_PEDAL_MAX:              return 0x60000555
            case Param.WAH_LEVEL:                  return 0x60000556
            case Param.WAH_DIRECT_MIX:             return 0x60000557
            case Param.PEDAL_BEND_PITCH:           return 0x60000558
            case Param.PEDAL_BEND_POSITION:        return 0x60000559
            case Param.PEDAL_BEND_LEVEL:           return 0x6000055A
            case Param.PEDAL_BEND_DIRECT_MIX:      return 0x6000055B
            case Param.WAH_95E_POSITION:           return 0x6000055C
            case Param.WAH_95E_PEDAL_MIN:          return 0x6000055D
            case Param.WAH_95E_PEDAL_MAX:          return 0x6000055E
            case Param.WAH_95E_LEVEL:              return 0x6000055F
            case Param.WAH_95E_DIRECT_MIX:         return 0x60000560
            case Param.FOOT_VOLUME:                return 0x60000561
            case Param.SEND_RETURN_SWITCH:         return 0x60000562
            case Param.SEND_RETURN_MODE:           return 0x60000563
            case Param.SEND_RETURN_SEND_LEVEL:     return 0x60000564
            case Param.SEND_RETURN_RETURN_LEVEL:   return 0x60000565
            case Param.NOISE_SUPPRESSOR_SWITCH:    return 0x60000566
            case Param.NOISE_SUPPRESSOR_THRESHOLD: return 0x60000567
            case Param.NOISE_SUPPRESSOR_RELEASE:   return 0x60000568
            case Param.MASTER_KEY:                 return 0x60000571
            case Param.SOLO_SWITCH:                return 0x60000614
            case Param.SOLO_LEVEL:                 return 0x60000615
            case Param.CONTOUR_SWITCH:             return 0x60000616
            case Param.CONTOUR_SELECT:             return 0x60000617
            case Param.SEND_RETURN_POSITION:       return 0x60000621
            case Param.EQ_POSITION:                return 0x60000622
            case Param.PEDAL_POSITION:             return 0x60000623
            case Param.CABINET_RESONANCE:          return 0x60000643
            case Param.PANEL_AMP_TYPE:             return 0x60000650
            case Param.VARIATION:                  return 0x6000065C
            case Param.LED_BOOST:                  return 0x6000065D
            case Param.LED_MOD:                    return 0x6000065E
            case Param.LED_FX:                     return 0x6000065F
            case Param.LED_DELAY:                  return 0x60000660
            case Param.LED_REVERB:                 return 0x60000661
            case Param.CONTOUR1_TYPE:              return 0x60000F30
            case Param.CONTOUR1_FREQ_SHIFT:        return 0x60000F31
            case Param.CONTOUR2_TYPE:              return 0x60000F38
            case Param.CONTOUR2_FREQ_SHIFT:        return 0x60000F39
            case Param.CONTOUR3_TYPE:              return 0x60000F40
            case Param.CONTOUR3_FREQ_SHIFT:        return 0x60000F41
            case Param.SOLO_EQ_SWITCH:             return 0x60000F11
            case Param.SOLO_EQ_LOW_CUT:            return 0x60000F12
            case Param.SOLO_EQ_LOW_GAIN:           return 0x60000F13
            case Param.SOLO_EQ_MID_FREQ:           return 0x60000F14
            case Param.SOLO_EQ_MID_Q:              return 0x60000F15
            case Param.SOLO_EQ_MID_GAIN:           return 0x60000F16
            case Param.SOLO_EQ_HIGH_GAIN:          return 0x60000F17
            case Param.SOLO_EQ_HIGH_CUT:           return 0x60000F18
            case Param.SOLO_EQ_LEVEL:              return 0x60000F19
            case Param.SOLO_DELAY_SWITCH:          return 0x60000F1A
            case Param.SOLO_DELAY_CARRYOVER:       return 0x60000F1B
            case Param.SOLO_DELAY_TIME:            return 0x60000F1C
            case Param.SOLO_DELAY_FEEDBACK:        return 0x60000F1E
            case Param.SOLO_DELAY_LEVEL:           return 0x60000F1F
            case Param.SOLO_DELAY_DIRECT_MIX:      return 0x60000F20
            case Param.SOLO_DELAY_FILTER:          return 0x60000F21
            case Param.SOLO_DELAY_HIGH_CUT:        return 0x60000F22
            case Param.SOLO_DELAY_MOD_SWITCH:      return 0x60000F23
            case Param.SOLO_DELAY_MOD_RATE:        return 0x60000F24
            case Param.SOLO_DELAY_MOD_DEPTH:       return 0x60000F25
            case Param.EQ2_POSITION:               return 0x60000619
            # The system area, from 0x00000000.
            case Param.GLOBAL_EQ_SWITCH:           return 0x00000010
            case Param.GLOBAL_EQ_TYPE:             return 0x00000011
            case Param.GLOBAL_EQ_POSITION:         return 0x00000012
            case Param.LINE_OUT_AIR_FEEL:          return 0x00000029
            case Param.STEREO_EXPAND:              return 0x0000002A
            case Param.GLOBAL_EQ_SELECT:           return 0x0000002E
            case Param.LINE_OUT_CUSTOM_SWITCH:     return 0x00000110
            case Param.LINE_OUT_CUSTOM_SELECT:     return 0x00000111
            case Param.LINE_OUT_CUSTOM1_MIC_TYPE:  return 0x00000112
            case Param.LINE_OUT_CUSTOM1_MIC_DISTANCE:  return 0x00000113
            case Param.LINE_OUT_CUSTOM1_MIC_POSITION:  return 0x00000114
            case Param.LINE_OUT_CUSTOM2_MIC_TYPE:  return 0x00000118
            case Param.LINE_OUT_CUSTOM2_MIC_DISTANCE:  return 0x00000119
            case Param.LINE_OUT_CUSTOM2_MIC_POSITION:  return 0x0000011A
        # Not listed above: a copy of another setting's layout.
        twin, shift = self.twin_and_shift()
        return twin.address() + shift

    def size(self) -> int:
        """Bytes the amp stores it in. Two bytes are 7-bit halves."""
        if self in EFFECT_KNOBS:
            return EFFECT_KNOBS[self][2].size
        if self.twin() is not None:
            return self.twin().size()
        return 2 if self in (Param.DELAY_TIME, Param.REVERB_PRE_DELAY, Param.SOLO_DELAY_TIME) else 1

    def offset(self) -> int:
        """What the amp adds before storing it, e.g. 24 for a -24..+24 dB
        band stored as 0-48. Real value = stored - offset."""
        if self in EFFECT_KNOBS:
            return EFFECT_KNOBS[self][2].stored_offset
        if self.twin() is not None:
            return self.twin().offset()
        match self:
            case _ if self.is_eq_band() or self is Param.EQ_LEVEL:  return 24
            case (
                Param.EQ_LOW_GAIN | Param.EQ_LOW_MID_GAIN | Param.EQ_HIGH_MID_GAIN |
                Param.EQ_HIGH_GAIN | Param.EQ_PEQ_LEVEL
            ):
                return 20
            case (
                Param.BOOST_BOTTOM | Param.BOOST_TONE | Param.CONTOUR1_FREQ_SHIFT |
                Param.CONTOUR2_FREQ_SHIFT | Param.CONTOUR3_FREQ_SHIFT
            ):
                return 50
            # The solo EQ's gains go to +-24, not +-20 like the other EQs.
            case (
                Param.PEDAL_BEND_PITCH | Param.SOLO_EQ_LOW_GAIN | Param.SOLO_EQ_MID_GAIN |
                Param.SOLO_EQ_HIGH_GAIN | Param.SOLO_EQ_LEVEL
            ):
                return 24
            # Reverb time shows 1-100 (0.1 s steps) but is stored 0-99.
            case Param.REVERB_TIME:       return -1
            case _:                       return 0

    # --- What sort of control it is ---------------------------------------

    def kind(self) -> Kind:
        if self in EFFECT_KNOBS:
            return EFFECT_KNOBS[self][2].kind()
        if self.twin() is not None:
            return self.twin().kind()
        match self:
            case _ if self.options() is not None:  return Kind.ENUM
            case _ if self.value.endswith("_switch"):  return Kind.TOGGLE
            case (
                Param.BRIGHT | Param.VARIATION | Param.DELAY_SDE_FILTER |
                Param.SOLO_DELAY_CARRYOVER | Param.STEREO_EXPAND
            ):
                return Kind.TOGGLE
            case _:
                return Kind.RANGE

    def range(self) -> tuple[int, int]:
        """(lowest, highest), in real units."""
        if self in EFFECT_KNOBS:
            knob = EFFECT_KNOBS[self][2]
            return (knob.low, knob.high)
        if self.twin() is not None:
            return self.twin().range()
        if self in COLOUR_SETTINGS:
            source = COLOUR_SETTINGS[self][1]
            # A colour's effect type has the same range as the block's own type.
            return source.range() if isinstance(source, Param) else (0, len(source) - 1)
        match self:
            # The amp accepts numbers Tone Studio never offers (the gaps in
            # the option lists), so these go wider than their option tables.
            case Param.BOOST_TYPE:                          return (0, 25)
            case Param.FX1_TYPE | Param.FX2_TYPE:           return (0, 40)
            case Param.DELAY_TYPE:                          return (0, 10)
            case Param.REVERB_TYPE:                         return (0, 6)
            case _ if self.kind() is Kind.ENUM:             return (min(self.options()), max(self.options()))
            case _ if self.kind() is Kind.TOGGLE:           return (0, 1)
            case _ if self.is_eq_band() or self is Param.EQ_LEVEL:  return (-24, 24)
            case Param.GAIN | Param.BOOST_DRIVE:            return (0, 120)
            case Param.BOOST_BOTTOM | Param.BOOST_TONE:     return (-50, 50)
            case (
                Param.CONTOUR1_FREQ_SHIFT | Param.CONTOUR2_FREQ_SHIFT | Param.CONTOUR3_FREQ_SHIFT
            ):
                return (-50, 50)
            case Param.CONTOUR1_TYPE | Param.CONTOUR2_TYPE | Param.CONTOUR3_TYPE:  return (0, 3)
            case (
                Param.EQ_LOW_GAIN | Param.EQ_LOW_MID_GAIN | Param.EQ_HIGH_MID_GAIN |
                Param.EQ_HIGH_GAIN | Param.EQ_PEQ_LEVEL
            ):
                return (-20, 20)
            case _ if self.steps() is not None:             return (0, len(self.steps()) - 1)
            case Param.DELAY_TIME | Param.SOLO_DELAY_TIME:  return (1, 2000)
            case Param.DELAY_LEVEL | Param.SOLO_DELAY_LEVEL:  return (0, 120)
            case Param.REVERB_TIME:                         return (1, 100)
            case Param.REVERB_PRE_DELAY:                    return (0, 500)
            case Param.REVERB_DENSITY:                      return (0, 10)
            case (
                Param.PEDAL_BEND_PITCH | Param.SOLO_EQ_LOW_GAIN | Param.SOLO_EQ_MID_GAIN |
                Param.SOLO_EQ_HIGH_GAIN | Param.SOLO_EQ_LEVEL
            ):
                return (-24, 24)
            case _:                                         return (0, 100)

    def unit(self) -> str | None:
        if self in EFFECT_KNOBS:
            _, effect, knob = EFFECT_KNOBS[self]
            # The FX-slot EQs' gains are the -20..+20 ones.
            if effect.key.endswith("_eq") and knob.stored_offset == 20:
                return "dB"
            if knob.key.startswith("pre_delay") or knob.key == "echo_repeat_rate":
                return "ms"
            return None
        if self.twin() is not None:
            return self.twin().unit()
        match self:
            case Param.DELAY_TIME | Param.REVERB_PRE_DELAY | Param.SOLO_DELAY_TIME:  return "ms"
            case _ if self.is_eq_band() or self is Param.EQ_LEVEL:               return "dB"
            case (
                Param.EQ_LOW_GAIN | Param.EQ_LOW_MID_GAIN | Param.EQ_HIGH_MID_GAIN |
                Param.EQ_HIGH_GAIN | Param.EQ_PEQ_LEVEL | Param.SOLO_EQ_LOW_GAIN |
                Param.SOLO_EQ_MID_GAIN | Param.SOLO_EQ_HIGH_GAIN | Param.SOLO_EQ_LEVEL
            ):
                return "dB"
            case _:                                     return None

    def is_writable(self) -> bool:
        """False for the settings the amp reports but ignores writes to."""
        return self not in (Param.KNOB_VOLUME, Param.PANEL_AMP_TYPE, Param.VARIATION) and not self.value.startswith("led_")

    def steps(self) -> tuple[str, ...] | None:
        """Text for each step of a stepped knob, lowest first - what Tone
        Studio prints instead of the raw number ("1.25 kHz", not 19)."""
        if self in EFFECT_KNOBS:
            return EFFECT_KNOBS[self][2].steps
        if self.twin() is not None:
            return self.twin().steps()
        match self:
            case Param.EQ_LOW_CUT | Param.REVERB_LOW_CUT | Param.SOLO_EQ_LOW_CUT:  return LOW_CUT
            case Param.EQ_LOW_MID_FREQ | Param.EQ_HIGH_MID_FREQ | Param.SOLO_EQ_MID_FREQ:  return FREQUENCY
            case Param.EQ_LOW_MID_Q | Param.EQ_HIGH_MID_Q | Param.SOLO_EQ_MID_Q:  return Q
            case (
                Param.EQ_HIGH_CUT | Param.REVERB_HIGH_CUT | Param.DELAY_HIGH_CUT |
                Param.SOLO_EQ_HIGH_CUT | Param.SOLO_DELAY_HIGH_CUT
            ):
                return HIGH_CUT
            case Param.LINE_OUT_CUSTOM1_MIC_DISTANCE | Param.LINE_OUT_CUSTOM2_MIC_DISTANCE:
                return tuple(f"{centimetres} cm" for centimetres in range(21))
            case Param.LINE_OUT_CUSTOM1_MIC_POSITION | Param.LINE_OUT_CUSTOM2_MIC_POSITION:
                return tuple(f"{centimetres} cm" for centimetres in range(11))
            case _:                                         return None

    def options(self) -> dict[int, str] | None:
        """The named values of a setting that is one of a set."""
        if self in EFFECT_KNOBS:
            return EFFECT_KNOBS[self][2].options
        if self.twin() is not None:
            return self.twin().options()
        if self in COLOUR_SETTINGS:
            source = COLOUR_SETTINGS[self][1]
            return source.options() if isinstance(source, Param) else source
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
                    # 28-32 are accepted by the MkII but named nowhere - not even in
                    # Tone Studio, which only ever shows panel_amp_type + variation.
                    # Reading amp_type after each panel TYPE/VARIATION combination
                    # would name them.
                    0x1C: "MkII amp 28",
                    0x1D: "MkII amp 29",
                    0x1E: "MkII amp 30",
                    0x1F: "MkII amp 31",
                    0x20: "MkII amp 32",
                }
            case Param.PANEL_AMP_TYPE:
                return {0: "Acoustic", 1: "Clean", 2: "Crunch", 3: "Lead", 4: "Brown"}
            case Param.CABINET_RESONANCE:
                return {0: "Vintage", 1: "Modern", 2: "Deep"}
            case Param.CONTOUR_SELECT:
                return {0: "Contour 1", 1: "Contour 2", 2: "Contour 3"}
            case Param.BOOST_TYPE:
                return {
                    0x00: "Mid Boost", 0x01: "Clean Boost", 0x02: "Treble Boost",
                    0x03: "Crunch OD", 0x04: "Natural OD", 0x05: "Warm OD",
                    0x06: "Fat DS", 0x08: "Metal DS", 0x09: "Oct Fuzz",
                    0x0A: "Blues Drive", 0x0B: "Overdrive", 0x0C: "T-Scream",
                    0x0D: "Turbo OD", 0x0E: "Distortion", 0x0F: "Rat",
                    0x10: "Guv DS", 0x11: "DST+", 0x12: "Metal Zone",
                    0x13: "'60s Fuzz", 0x14: "Muff Fuzz", 0x15: "HM-2",
                    0x16: "Metal Core", 0x17: "Centa OD",
                }
            case Param.EQ_TYPE:
                return {0: "Parametric", 1: "GE-10"}
            case Param.EQ_POSITION:
                return {0: "Amp In", 1: "Amp Out"}
            case Param.FX1_TYPE | Param.FX2_TYPE:
                # Effect types for the FX1/FX2 slots, from effects.py.
                return {effect.type: effect.name for effect in EFFECTS}
            case Param.DELAY_TYPE:
                return {
                    0x00: "Digital", 0x01: "Pan", 0x02: "Stereo", 0x06: "Reverse",
                    0x07: "Analog", 0x08: "Tape Echo", 0x09: "Modulate", 0x0A: "SDE-3000",
                }
            case Param.DELAY_SDE_RANGE:
                return {0: "8 kHz", 1: "17 kHz"}
            case Param.DELAY_SDE_FEEDBACK_PHASE | Param.DELAY_SDE_DELAY_PHASE:
                return {0: "Normal", 1: "Inverse"}
            case _ if self.value.startswith("led_"):
                # Channel colours as reported by the led_* parameters. The numbers are what
                # the amp reports; the colour names are the documented convention and are
                # unconfirmed by eye. Writing these does not move the panel LEDs.
                return {0x00: "off", 0x01: "green", 0x02: "red", 0x03: "yellow"}
            case Param.REVERB_TYPE:
                # The five Tone Studio offers. 0 and 2 are accepted but never shown.
                return {0x01: "Room", 0x03: "Hall", 0x04: "Plate", 0x05: "Spring", 0x06: "Modulate"}
            case Param.PEDAL_TYPE:
                # What the expression pedal section is doing, for pedal_type.
                return {0x00: "Wah", 0x01: "Pedal Bend", 0x02: "Wah 95E"}
            case Param.PEDAL_POSITION:
                return {0: "Input", 1: "Post Amp"}
            case Param.WAH_TYPE:
                # The pedal wah voicings, for wah_type.
                return {
                    0x00: "Cry Wah",
                    0x01: "Vo Wah",
                    0x02: "Fat Wah",
                    0x03: "Light Wah",
                    0x04: "7 String Wah",
                    0x05: "Reso Wah",
                }
            case Param.SEND_RETURN_MODE:
                return {0: "Series", 1: "Parallel"}
            case Param.SEND_RETURN_POSITION:
                return {0: "Post Amp", 1: "Post Reverb"}
            case Param.MASTER_KEY:
                return {
                    0: "C (Am)", 1: "Db (Bbm)", 2: "D (Bm)", 3: "Eb (Cm)",
                    4: "E (C#m)", 5: "F (Dm)", 6: "F# (D#m)", 7: "G (Em)",
                    8: "Ab (Fm)", 9: "A (F#m)", 10: "Bb (Gm)", 11: "B (G#m)",
                }
            case Param.EQ2_POSITION:
                return {0: "Amp In", 1: "Amp Out"}
            case Param.SOLO_DELAY_FILTER:
                return {0: "Off", 1: "Analog", 2: "Tape Echo"}
            case Param.GLOBAL_EQ_POSITION:
                return {0: "Input", 1: "Output", 2: "Line Out", 3: "Speaker Out"}
            case Param.GLOBAL_EQ_SELECT:
                # Roland names the three stored global EQs by colour.
                return {0: "Green", 1: "Red", 2: "Yellow"}
            case Param.LINE_OUT_AIR_FEEL:
                return {0: "Rec", 1: "Live", 2: "Blend"}
            case Param.LINE_OUT_CUSTOM_SELECT:
                return {0: "Custom 1", 1: "Custom 2"}
            case Param.LINE_OUT_CUSTOM1_MIC_TYPE | Param.LINE_OUT_CUSTOM2_MIC_TYPE:
                return {0: "DYN57", 1: "DYN421", 2: "CND451", 3: "CND87", 4: "RBN121"}
            case _:
                return None

    def group(self) -> str:
        """The UI section this setting belongs to."""
        if self in EFFECT_KNOBS:
            return f"fx{EFFECT_KNOBS[self][0]}"
        match self:
            case _ if self.value.startswith("color_"):            return "colors"
            case _ if self.value.startswith(("global_", "line_out_")) or self is Param.STEREO_EXPAND:
                return "global"
            case _ if self.value.startswith(("solo_eq_", "solo_delay_")):  return "solo"
            case _ if self.value.startswith("eq2_"):              return "eq2"
            case _ if self.value.startswith("eq_"):               return "eq"
            case _ if self.value.startswith("boost_"):            return "boost"
            case _ if self.value.startswith("delay2_"):           return "delay2"
            case _ if self.value.startswith("delay_"):            return "delay"
            case _ if self.value.startswith("reverb_"):           return "reverb"
            case _ if self.value.startswith(("wah_", "pedal_")) or self is Param.FOOT_VOLUME:
                return "wah"
            case _ if self.value.startswith("fx1_"):              return "fx1"
            case _ if self.value.startswith("fx2_"):              return "fx2"
            case _ if self.value.startswith("send_return_"):      return "send_return"
            case _ if self.value.startswith("noise_suppressor_"): return "noise_gate"
            case _ if self.value.startswith("led_"):              return "channels"
            case Param.MASTER_KEY:                                return "effects"
            case _:
                return "amp"

    def effect(self) -> tuple[int, int, str] | None:
        """For an FX-slot knob: (slot, effect TYPE value, knob label)."""
        if self not in EFFECT_KNOBS:
            return None
        slot, effect, knob = EFFECT_KNOBS[self]
        return (slot, effect.type, knob.label)

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
        effect = self.effect()
        entry = {
            "name": self.value,
            "group": self.group(),
            "kind": self.kind().value,
            "min": low,
            "max": high,
            "writable": self.is_writable(),
            "unit": self.unit(),
            "options": {str(number): label for number, label in options.items()} if options else None,
            "steps": list(self.steps()) if self.steps() else None,
            "slot": effect[0] if effect else None,
            "effect": effect[1] if effect else None,
            "label": effect[2] if effect else None,
        }
        return {key: value for key, value in entry.items() if value is not None}

    # --- Helpers -----------------------------------------------------------

    def is_eq_band(self) -> bool:
        return self.value.startswith("eq_band_")

    def twin_and_shift(self) -> tuple["Param | None", int]:
        """For a copy of another setting's layout (see TWINS): that setting,
        and how far from it this one lives. (None, 0) for anything else."""
        if self.value not in NOT_TWINS:
            for prefix, twin_prefix, shift in TWINS:
                if self.value.startswith(prefix):
                    return Param(twin_prefix + self.value.removeprefix(prefix)), shift
        return None, 0

    def twin(self) -> "Param | None":
        """The setting this one copies: delay2_feedback -> delay_feedback."""
        return self.twin_and_shift()[0]

    @classmethod
    def eq_bands(cls) -> list["Param"]:
        """The ten graphic EQ bands, low to high."""
        return [param for param in cls if param.is_eq_band()]

    @classmethod
    def schema(cls) -> list[dict]:
        """Every setting, described for the UI, in the order defined above -
        so an effect's knobs arrive in the same order as on Tone Studio."""
        return [param.describe() for param in cls]


# Every FX-slot knob -> (slot, effect, knob), for the methods above. Built
# here because the members only exist once the class body has finished.
EFFECT_KNOBS = {
    Param(f"fx{slot}_{effect.key}_{knob.key}"): (slot, effect, knob)
    for slot in SLOT_BASE
    for effect in EFFECTS
    for knob in effect.knobs
}

# Every colour-channel setting -> (address, where its choices come from):
# a Param whose options and range it shares, or its own {value: name}.
# The amp stores them as one run from 0x60000624: six blocks x three
# colours, the three layer modes, then each block's selected colour.
_COLOUR_TYPES = {
    "boost": Param.BOOST_TYPE, "mod": Param.FX1_TYPE, "fx": Param.FX1_TYPE,
    "delay": Param.DELAY_TYPE, "reverb": Param.REVERB_TYPE, "delay2": Param.DELAY_TYPE,
}
COLOUR_SETTINGS = {}
for block_index, block in enumerate(COLOUR_BLOCKS):
    for colour_index, colour in enumerate(COLOURS):
        COLOUR_SETTINGS[Param(f"color_{block}_{colour}")] = (
            COLOUR_BASE + block_index * 3 + colour_index, _COLOUR_TYPES[block],
        )
for colour_index, colour in enumerate(COLOURS):
    COLOUR_SETTINGS[Param(f"color_layer_{colour}")] = (
        COLOUR_BASE + 18 + colour_index, {0: "Delay", 1: "Delay + Reverb", 2: "Reverb"},
    )
for block_index, block in enumerate(COLOUR_BLOCKS[:5]):
    COLOUR_SETTINGS[Param(f"color_select_{block}")] = (
        COLOUR_BASE + 21 + block_index, {0: "Green", 1: "Red", 2: "Yellow"},
    )
