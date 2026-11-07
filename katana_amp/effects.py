"""The effects an FX slot can hold, and every effect's own knobs.

    from katana_amp.effects import EFFECTS, effect_for

    effect_for(19).name            "Phaser"
    effect_for(19).knobs[1].key    "rate"   ->  Param.FX1_PHASER_RATE / FX2_PHASER_RATE

The amp has two FX slots (MOD = slot 1, FX = slot 2). Each slot has one
block of memory holding the settings of *every* effect type at once - the
slot's TYPE picks which one you hear. So a knob here exists twice, once per
slot, and param.py turns each one into an fx1_... and an fx2_... setting.

Source: BOSS Tone Studio for KATANA MkII ships Roland's own address map
(js/config/address_map.js, unpacked to AppData while the app runs). The
table below is that map's Fx block, with Tone Studio's labels. `offset` is
written the way Roland writes it - already in the amp's 7-bit form, so
0x103 is the byte after 0x07F, not 0x080.
"""

from dataclasses import dataclass

from katana_amp.kind import Kind

# Where each slot's block starts in the amp's live area.
SLOT_BASE = {1: 0x60000100, 2: 0x60000300}


@dataclass(frozen=True)
class Knob:
    key: str                  # "rate"; the setting is fx1_<effect>_<key>
    label: str                # what the editor prints under it
    offset: int               # where it sits inside the slot's block
    low: int                  # range in real units, as Tone Studio shows it
    high: int
    stored_offset: int = 0    # the amp stores value + this (so -50..50 -> 0..100)
    size: int = 1             # 2 = a value above 127, split into 7-bit halves
    options: dict[int, str] | None = None   # named choices -> a dropdown
    steps: tuple[str, ...] | None = None    # text for each step of a knob

    def kind(self) -> Kind:
        if self.options:
            return Kind.ENUM
        if (self.low, self.high) == (0, 1):
            return Kind.TOGGLE
        return Kind.RANGE


@dataclass(frozen=True)
class Effect:
    type: int                 # the slot's TYPE value that selects it
    key: str                  # "phaser"
    name: str                 # "Phaser"
    knobs: tuple[Knob, ...]


# --- Value text shared by several knobs --------------------------------------
# Tone Studio prints these instead of the raw step number.

LOW_CUT = ("FLAT", "20.0 Hz", "25.0 Hz", "31.5 Hz", "40.0 Hz", "50.0 Hz", "63.0 Hz", "80.0 Hz", "100 Hz", "125 Hz", "160 Hz", "200 Hz", "250 Hz", "315 Hz", "400 Hz", "500 Hz", "630 Hz", "800 Hz")
FREQUENCY = ("20.0 Hz", "25.0 Hz", "31.5 Hz", "40.0 Hz", "50.0 Hz", "63.0 Hz", "80.0 Hz", "100 Hz", "125 Hz", "160 Hz", "200 Hz", "250 Hz", "315 Hz", "400 Hz", "500 Hz", "630 Hz", "800 Hz", "1.00 kHz", "1.25 kHz", "1.60 kHz", "2.00 kHz", "2.50 kHz", "3.15 kHz", "4.00 kHz", "5.00 kHz", "6.30 kHz", "8.00 kHz", "10.0 kHz")
Q = ("0.5", "1", "2", "4", "8", "16")
HIGH_CUT = ("630 Hz", "800 Hz", "1.00 kHz", "1.25 kHz", "1.60 kHz", "2.00 kHz", "2.50 kHz", "3.15 kHz", "4.00 kHz", "5.00 kHz", "6.30 kHz", "8.00 kHz", "10.0 kHz", "12.5 kHz", "FLAT")
HARMONY = ("-2oct", "-14th", "-13th", "-12th", "-11th", "-10th", "-9th", "-1oct", "-7th", "-6th", "-5th", "-4th", "-3rd", "-2nd", "UNISON", "+2nd", "+3rd", "+4th", "+5th", "+6th", "+7th", "+1oct", "+9th", "+10th", "+11th", "+12th", "+13th", "+14th", "+2oct", "USER")
CROSSOVER = ("100 Hz", "125 Hz", "160 Hz", "200 Hz", "250 Hz", "315 Hz", "400 Hz", "500 Hz", "630 Hz", "800 Hz", "1.00 kHz", "1.25 kHz", "1.60 kHz", "2.00 kHz", "2.50 kHz", "3.15 kHz", "4.00 kHz")
LIMITER_RATIO = ("1:1", "1.2:1", "1.4:1", "1.6:1", "1.8:1", "2:1", "2.3:1", "2.6:1", "3:1", "3.5:1", "4:1", "5:1", "6:1", "8:1", "10:1", "12:1", "20:1", "INF:1")
CHORUS_PRE_DELAY = tuple(f"{tenths / 2:.1f} ms" for tenths in range(81))
STEP_RATE = ("OFF", *(str(number) for number in range(101)))


# --- The table -----------------------------------------------------------------
# Every effect type, in TYPE order. Types 5, 8, 11, 13, 17, 24, 30 and 32-34
# are accepted by the amp but Tone Studio never offers them.

EFFECTS = (
    Effect(0, "t_wah", "T Wah", (
        Knob("mode", "Mode", 0x002, 0, 1, options={0: "LPF", 1: "BPF"}),
        Knob("polarity", "Polarity", 0x003, 0, 1, options={0: "Down", 1: "Up"}),
        Knob("sens", "Sens", 0x004, 0, 100),
        Knob("frequency", "Freq", 0x005, 0, 100),
        Knob("peak", "Peak", 0x006, 0, 100),
        Knob("direct_mix", "Direct", 0x007, 0, 100),
        Knob("level", "Level", 0x008, 0, 100),
    )),
    Effect(1, "auto_wah", "Auto Wah", (
        Knob("mode", "Mode", 0x009, 0, 1, options={0: "LPF", 1: "BPF"}),
        Knob("frequency", "Freq", 0x00A, 0, 100),
        Knob("peak", "Peak", 0x00B, 0, 100),
        Knob("rate", "Rate", 0x00C, 0, 100),
        Knob("depth", "Depth", 0x00D, 0, 100),
        Knob("direct_mix", "Direct", 0x00E, 0, 100),
        Knob("level", "Level", 0x00F, 0, 100),
    )),
    Effect(2, "pedal_wah", "Pedal Wah", (
        Knob("type", "Type", 0x010, 0, 5, options={0: "Cry Wah", 1: "Vo Wah", 2: "Fat Wah", 3: "Light Wah", 4: "7 String Wah", 5: "Reso Wah"}),
        Knob("position", "Pedal", 0x011, 0, 100),
        Knob("pedal_min", "Pedal Min", 0x012, 0, 100),
        Knob("pedal_max", "Pedal Max", 0x013, 0, 100),
        Knob("level", "Level", 0x014, 0, 100),
        Knob("direct_mix", "Direct", 0x015, 0, 100),
    )),
    Effect(3, "comp", "Comp", (
        Knob("type", "Type", 0x016, 0, 6, options={0: "Boss Comp", 1: "Hi-Band", 2: "Light", 3: "D-Comp", 4: "Orange", 5: "Fat", 6: "Mild"}),
        Knob("sustain", "Sustain", 0x017, 0, 100),
        Knob("attack", "Attack", 0x018, 0, 100),
        Knob("tone", "Tone", 0x019, -50, 50, stored_offset=50),
        Knob("level", "Level", 0x01A, 0, 100),
    )),
    Effect(4, "limiter", "Limiter", (
        Knob("type", "Type", 0x01B, 0, 2, options={0: "Boss Limiter", 1: "Rack 160D", 2: "Vintage Rack U"}),
        Knob("attack", "Attack", 0x01C, 0, 100),
        Knob("threshold", "Thresh", 0x01D, 0, 100),
        Knob("ratio", "Ratio", 0x01E, 0, 17, steps=LIMITER_RATIO),
        Knob("release", "Release", 0x01F, 0, 100),
        Knob("level", "Level", 0x020, 0, 100),
    )),
    Effect(6, "graphic_eq", "Graphic EQ", (
        Knob("band_31hz", "31", 0x021, -20, 20, stored_offset=20),
        Knob("band_62hz", "62", 0x022, -20, 20, stored_offset=20),
        Knob("band_125hz", "125", 0x023, -20, 20, stored_offset=20),
        Knob("band_250hz", "250", 0x024, -20, 20, stored_offset=20),
        Knob("band_500hz", "500", 0x025, -20, 20, stored_offset=20),
        Knob("band_1khz", "1k", 0x026, -20, 20, stored_offset=20),
        Knob("band_2khz", "2k", 0x027, -20, 20, stored_offset=20),
        Knob("band_4khz", "4k", 0x028, -20, 20, stored_offset=20),
        Knob("band_8khz", "8k", 0x029, -20, 20, stored_offset=20),
        Knob("band_16khz", "16k", 0x02A, -20, 20, stored_offset=20),
        Knob("level", "Level", 0x02B, -20, 20, stored_offset=20),
    )),
    Effect(7, "parametric_eq", "Parametric EQ", (
        Knob("low_cut", "Low Cut", 0x02C, 0, 17, steps=LOW_CUT),
        Knob("low_gain", "Low", 0x02D, -20, 20, stored_offset=20),
        Knob("low_mid_freq", "Lo-Mid Freq", 0x02E, 0, 27, steps=FREQUENCY),
        Knob("low_mid_q", "Lo-Mid Q", 0x02F, 0, 5, steps=Q),
        Knob("low_mid_gain", "Lo-Mid", 0x030, -20, 20, stored_offset=20),
        Knob("high_mid_freq", "Hi-Mid Freq", 0x031, 0, 27, steps=FREQUENCY),
        Knob("high_mid_q", "Hi-Mid Q", 0x032, 0, 5, steps=Q),
        Knob("high_mid_gain", "Hi-Mid", 0x033, -20, 20, stored_offset=20),
        Knob("high_gain", "High", 0x034, -20, 20, stored_offset=20),
        Knob("high_cut", "High Cut", 0x035, 0, 14, steps=HIGH_CUT),
        Knob("level", "Level", 0x036, -20, 20, stored_offset=20),
    )),
    Effect(9, "guitar_sim", "Guitar Sim", (
        Knob("type", "Type", 0x037, 0, 7, options={0: "S->H", 1: "H->S", 2: "H->HF", 3: "S->Hollow", 4: "H->Hollow", 5: "S->AC", 6: "H->AC", 7: "P->AC"}),
        Knob("low", "Low", 0x038, -50, 50, stored_offset=50),
        Knob("high", "High", 0x039, -50, 50, stored_offset=50),
        Knob("level", "Level", 0x03A, 0, 100),
        Knob("body", "Body", 0x03B, 0, 100),
    )),
    Effect(10, "slow_gear", "Slow Gear", (
        Knob("sens", "Sens", 0x03C, 0, 100),
        Knob("rise_time", "Rise", 0x03D, 0, 100),
        Knob("level", "Level", 0x03E, 0, 100),
    )),
    Effect(12, "wave_synth", "Wave Synth", (
        Knob("wave", "Wave", 0x03F, 0, 1, options={0: "Saw", 1: "Square"}),
        Knob("cutoff", "Cutoff", 0x040, 0, 100),
        Knob("resonance", "Reso", 0x041, 0, 100),
        Knob("sens", "Sens", 0x042, 0, 100),
        Knob("decay", "Decay", 0x043, 0, 100),
        Knob("depth", "Depth", 0x044, 0, 100),
        Knob("level", "Level", 0x045, 0, 100),
        Knob("direct_mix", "Direct", 0x046, 0, 100),
    )),
    Effect(14, "octave", "Octave", (
        Knob("range", "Range", 0x047, 0, 3, options={0: "Range 1", 1: "Range 2", 2: "Range 3", 3: "Range 4"}),
        Knob("level", "Level", 0x048, 0, 100),
        Knob("direct_mix", "Direct", 0x049, 0, 100),
    )),
    Effect(15, "pitch_shifter", "Pitch Shifter", (
        Knob("voice", "Voice", 0x04A, 0, 1, options={0: "1 Voice", 1: "2 Voice"}),
        Knob("mode1", "1 Mode", 0x04B, 0, 3, options={0: "Fast", 1: "Medium", 2: "Slow", 3: "Mono"}),
        Knob("pitch1", "1 Pitch", 0x04C, -24, 24, stored_offset=24),
        Knob("fine1", "1 Fine", 0x04D, -50, 50, stored_offset=50),
        Knob("pre_delay1", "1 Pre-Dly", 0x04E, 0, 300, size=2),
        Knob("level1", "1 Level", 0x050, 0, 100),
        Knob("mode2", "2 Mode", 0x051, 0, 3, options={0: "Fast", 1: "Medium", 2: "Slow", 3: "Mono"}),
        Knob("pitch2", "2 Pitch", 0x052, -24, 24, stored_offset=24),
        Knob("fine2", "2 Fine", 0x053, -50, 50, stored_offset=50),
        Knob("pre_delay2", "2 Pre-Dly", 0x054, 0, 300, size=2),
        Knob("level2", "2 Level", 0x056, 0, 100),
        Knob("feedback", "Feedback", 0x057, 0, 100),
        Knob("direct_mix", "Direct", 0x058, 0, 100),
    )),
    Effect(16, "harmonist", "Harmonist", (
        Knob("voice", "Voice", 0x059, 0, 1, options={0: "1 Voice", 1: "2 Voice"}),
        Knob("harmony1", "1 Harmony", 0x05A, 0, 29, steps=HARMONY),
        Knob("pre_delay1", "1 Pre-Dly", 0x05B, 0, 300, size=2),
        Knob("level1", "1 Level", 0x05D, 0, 100),
        Knob("harmony2", "2 Harmony", 0x05E, 0, 29, steps=HARMONY),
        Knob("pre_delay2", "2 Pre-Dly", 0x05F, 0, 300, size=2),
        Knob("level2", "2 Level", 0x061, 0, 100),
        Knob("feedback", "Feedback", 0x062, 0, 100),
        Knob("direct_mix", "Direct", 0x063, 0, 100),
        Knob("user1_c", "1 C", 0x064, -24, 24, stored_offset=24),
        Knob("user1_db", "1 Db", 0x065, -24, 24, stored_offset=24),
        Knob("user1_d", "1 D", 0x066, -24, 24, stored_offset=24),
        Knob("user1_eb", "1 Eb", 0x067, -24, 24, stored_offset=24),
        Knob("user1_e", "1 E", 0x068, -24, 24, stored_offset=24),
        Knob("user1_f", "1 F", 0x069, -24, 24, stored_offset=24),
        Knob("user1_fs", "1 F#", 0x06A, -24, 24, stored_offset=24),
        Knob("user1_g", "1 G", 0x06B, -24, 24, stored_offset=24),
        Knob("user1_ab", "1 Ab", 0x06C, -24, 24, stored_offset=24),
        Knob("user1_a", "1 A", 0x06D, -24, 24, stored_offset=24),
        Knob("user1_bb", "1 Bb", 0x06E, -24, 24, stored_offset=24),
        Knob("user1_b", "1 B", 0x06F, -24, 24, stored_offset=24),
        Knob("user2_c", "2 C", 0x070, -24, 24, stored_offset=24),
        Knob("user2_db", "2 Db", 0x071, -24, 24, stored_offset=24),
        Knob("user2_d", "2 D", 0x072, -24, 24, stored_offset=24),
        Knob("user2_eb", "2 Eb", 0x073, -24, 24, stored_offset=24),
        Knob("user2_e", "2 E", 0x074, -24, 24, stored_offset=24),
        Knob("user2_f", "2 F", 0x075, -24, 24, stored_offset=24),
        Knob("user2_fs", "2 F#", 0x076, -24, 24, stored_offset=24),
        Knob("user2_g", "2 G", 0x077, -24, 24, stored_offset=24),
        Knob("user2_ab", "2 Ab", 0x078, -24, 24, stored_offset=24),
        Knob("user2_a", "2 A", 0x079, -24, 24, stored_offset=24),
        Knob("user2_bb", "2 Bb", 0x07A, -24, 24, stored_offset=24),
        Knob("user2_b", "2 B", 0x07B, -24, 24, stored_offset=24),
    )),
    Effect(18, "ac_processor", "AC Processor", (
        Knob("type", "Type", 0x07C, 0, 3, options={0: "Small", 1: "Medium", 2: "Bright", 3: "Power"}),
        Knob("bass", "Bass", 0x07D, -50, 50, stored_offset=50),
        Knob("middle", "Middle", 0x07E, -50, 50, stored_offset=50),
        Knob("middle_freq", "Mid Freq", 0x07F, 0, 27, steps=FREQUENCY),
        Knob("treble", "Treble", 0x100, -50, 50, stored_offset=50),
        Knob("presence", "Presence", 0x101, -50, 50, stored_offset=50),
        Knob("level", "Level", 0x102, 0, 100),
    )),
    Effect(19, "phaser", "Phaser", (
        Knob("type", "Type", 0x103, 0, 3, options={0: "4 Stage", 1: "8 Stage", 2: "12 Stage", 3: "BiPhase"}),
        Knob("rate", "Rate", 0x104, 0, 100),
        Knob("depth", "Depth", 0x105, 0, 100),
        Knob("manual", "Manual", 0x106, 0, 100),
        Knob("resonance", "Reso", 0x107, 0, 100),
        Knob("step_rate", "Step", 0x108, -1, 100, stored_offset=1, steps=STEP_RATE),
        Knob("level", "Level", 0x109, 0, 100),
        Knob("direct_mix", "Direct", 0x10A, 0, 100),
    )),
    Effect(20, "flanger", "Flanger", (
        Knob("rate", "Rate", 0x10B, 0, 100),
        Knob("depth", "Depth", 0x10C, 0, 100),
        Knob("manual", "Manual", 0x10D, 0, 100),
        Knob("resonance", "Reso", 0x10E, 0, 100),
        Knob("low_cut", "Low Cut", 0x110, 0, 10, steps=("FLAT", "55 Hz", "110 Hz", "165 Hz", "200 Hz", "280 Hz", "340 Hz", "400 Hz", "500 Hz", "630 Hz", "800 Hz")),
        Knob("level", "Level", 0x111, 0, 100),
        Knob("direct_mix", "Direct", 0x112, 0, 100),
    )),
    Effect(21, "tremolo", "Tremolo", (
        Knob("waveshape", "Wave", 0x113, 0, 100),
        Knob("rate", "Rate", 0x114, 0, 100),
        Knob("depth", "Depth", 0x115, 0, 100),
        Knob("level", "Level", 0x116, 0, 100),
    )),
    Effect(22, "rotary", "Rotary", (
        Knob("rate_fast", "Rate", 0x119, 0, 100),
        Knob("depth", "Depth", 0x11C, 0, 100),
        Knob("level", "Level", 0x11D, 0, 100),
    )),
    Effect(23, "uni_v", "Uni-V", (
        Knob("rate", "Rate", 0x11E, 0, 100),
        Knob("depth", "Depth", 0x11F, 0, 100),
        Knob("level", "Level", 0x120, 0, 100),
    )),
    Effect(25, "slicer", "Slicer", (
        Knob("pattern", "Pattern", 0x121, 0, 19, steps=tuple(f"P{number}" for number in range(1, 21))),
        Knob("rate", "Rate", 0x122, 0, 100),
        Knob("trigger_sens", "Trig Sens", 0x123, 0, 100),
        Knob("level", "Level", 0x124, 0, 100),
        Knob("direct_mix", "Direct", 0x125, 0, 100),
    )),
    Effect(26, "vibrato", "Vibrato", (
        Knob("rate", "Rate", 0x126, 0, 100),
        Knob("depth", "Depth", 0x127, 0, 100),
        Knob("level", "Level", 0x12A, 0, 100),
    )),
    Effect(27, "ring_mod", "Ring Mod", (
        Knob("mode", "Mode", 0x12B, 0, 1, options={0: "Normal", 1: "Intelligent"}),
        Knob("frequency", "Freq", 0x12C, 0, 100),
        Knob("level", "Level", 0x12D, 0, 100),
        Knob("direct_mix", "Direct", 0x12E, 0, 100),
    )),
    Effect(28, "humanizer", "Humanizer", (
        Knob("mode", "Mode", 0x12F, 0, 1, options={0: "Picking", 1: "Auto"}),
        Knob("vowel1", "Vowel 1", 0x130, 0, 4, options={0: "A", 1: "E", 2: "I", 3: "O", 4: "U"}),
        Knob("vowel2", "Vowel 2", 0x131, 0, 4, options={0: "A", 1: "E", 2: "I", 3: "O", 4: "U"}),
        Knob("sens", "Sens", 0x132, 0, 100),
        Knob("rate", "Rate", 0x133, 0, 100),
        Knob("depth", "Depth", 0x134, 0, 100),
        Knob("manual", "Manual", 0x135, 0, 100),
        Knob("level", "Level", 0x136, 0, 100),
    )),
    Effect(29, "chorus", "Chorus", (
        Knob("crossover", "Crossover", 0x137, 0, 16, steps=CROSSOVER),
        Knob("low_rate", "Low Rate", 0x138, 0, 100),
        Knob("low_depth", "Low Depth", 0x139, 0, 100),
        Knob("low_pre_delay", "Low Pre-Dly", 0x13A, 0, 80, steps=CHORUS_PRE_DELAY),
        Knob("low_level", "Low Level", 0x13B, 0, 100),
        Knob("high_rate", "High Rate", 0x13C, 0, 100),
        Knob("high_depth", "High Depth", 0x13D, 0, 100),
        Knob("high_pre_delay", "High Pre-Dly", 0x13E, 0, 80, steps=CHORUS_PRE_DELAY),
        Knob("high_level", "High Level", 0x13F, 0, 100),
        Knob("direct_mix", "Direct", 0x140, 0, 100),
    )),
    Effect(31, "ac_guitar_sim", "AC Guitar Sim", (
        Knob("high", "High", 0x141, -50, 50, stored_offset=50),
        Knob("body", "Body", 0x142, 0, 100),
        Knob("low", "Low", 0x143, -50, 50, stored_offset=50),
        Knob("level", "Level", 0x145, 0, 100),
    )),
    Effect(35, "phaser_90e", "Phaser 90E", (
        Knob("script", "Script", 0x146, 0, 1),
        Knob("speed", "Speed", 0x147, 0, 100),
    )),
    Effect(36, "flanger_117e", "Flanger 117E", (
        Knob("manual", "Manual", 0x148, 0, 100),
        Knob("width", "Width", 0x149, 0, 100),
        Knob("speed", "Speed", 0x14A, 0, 100),
        Knob("regen", "Regen", 0x14B, 0, 100),
    )),
    Effect(37, "wah_95e", "Wah 95E", (
        Knob("position", "Pedal", 0x14C, 0, 100),
        Knob("pedal_min", "Pedal Min", 0x14D, 0, 100),
        Knob("pedal_max", "Pedal Max", 0x14E, 0, 100),
        Knob("level", "Level", 0x14F, 0, 100),
        Knob("direct_mix", "Direct", 0x150, 0, 100),
    )),
    Effect(38, "dc_30", "DC-30", (
        Knob("select", "Select", 0x151, 0, 1, options={0: "Chorus", 1: "Echo"}),
        Knob("input_volume", "Input", 0x152, 0, 100),
        Knob("chorus_intensity", "Chorus", 0x153, 0, 100),
        Knob("echo_repeat_rate", "Echo Rate", 0x154, 40, 600, size=2),
        Knob("echo_intensity", "Echo Int", 0x156, 0, 100),
        Knob("echo_volume", "Echo Vol", 0x157, 0, 100),
        Knob("tone", "Tone", 0x158, 0, 100),
        Knob("output", "Output", 0x159, 0, 1, options={0: "D+E", 1: "D/E"}),
    )),
    Effect(39, "heavy_octave", "Heavy Octave", (
        Knob("oct1_level", "1 Oct", 0x15A, 0, 100),
        Knob("oct2_level", "2 Oct", 0x15B, 0, 100),
        Knob("direct_mix", "Direct", 0x15C, 0, 100),
    )),
    Effect(40, "pedal_bend", "Pedal Bend", (
        Knob("pitch", "Pitch", 0x15D, -24, 24, stored_offset=24),
        Knob("position", "Pedal", 0x15E, 0, 100),
        Knob("level", "Level", 0x15F, 0, 100),
        Knob("direct_mix", "Direct", 0x160, 0, 100),
    )),
)


EFFECT_BY_TYPE = {effect.type: effect for effect in EFFECTS}


def effect_for(type_value: int) -> Effect | None:
    """The effect a slot's TYPE value selects, or None for an unused number."""
    return EFFECT_BY_TYPE.get(type_value)
