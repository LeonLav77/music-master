"""Plain-English helpers for every control on the Katana MkII.

There is only one amp, so the helpers share a single connection that opens
on first use. Nothing to pass around, nothing to close:

    from controls import *

    show_settings()
    set_gain(75)
    set_amp_type("5150 Drive")
    cry_wah()                 # load the Cry Wah and switch the pedal on
    sweep_wah(0, 100)

Naming follows the amp's own layout: `set_<section>_<control>`, e.g.
`set_reverb_level`, `set_boost_drive`, `set_delay_feedback`. Every setter
validates its range before anything is sent, and raises KatanaError rather
than letting a bad value reach the amp.

Anything without a dedicated helper is reachable by name:

    set_parameter("boost_bottom", 60)
    list_parameters()         # every name, with its range
"""

__all__ = [
    "connect", "disconnect", "amp_session",
    "get_parameter", "set_parameter", "list_parameters",
    "get_wide_parameter", "set_wide_parameter",
    # amp
    "get_gain", "set_gain", "get_volume", "set_volume",
    "get_bass", "set_bass", "get_middle", "set_middle",
    "get_treble", "set_treble", "get_presence", "set_presence",
    "get_knob_volume", "set_tone",
    "get_amp_type", "set_amp_type", "list_amp_types",
    "bright_on", "bright_off", "bright_is_on",
    # boost
    "boost_on", "boost_off", "boost_is_on",
    "get_boost_type", "set_boost_type", "list_boost_types",
    "get_boost_drive", "set_boost_drive",
    "get_boost_bottom", "set_boost_bottom",
    "get_boost_tone", "set_boost_tone",
    "get_boost_level", "set_boost_level",
    "get_boost_solo_level", "set_boost_solo_level",
    "get_boost_direct_mix", "set_boost_direct_mix",
    "boost_solo_on", "boost_solo_off", "boost_solo_is_on",
    # eq
    "eq_on", "eq_off", "eq_is_on", "get_eq_type", "set_eq_type",
    # fx slots
    "fx1_on", "fx1_off", "fx1_is_on", "get_fx1_type", "set_fx1_type",
    "fx2_on", "fx2_off", "fx2_is_on", "get_fx2_type", "set_fx2_type",
    "list_effect_types",
    # delay
    "delay_on", "delay_off", "delay_is_on",
    "get_delay_type", "set_delay_type", "list_delay_types",
    "get_delay_feedback", "set_delay_feedback",
    "get_delay_level", "set_delay_level",
    "get_delay_direct_mix", "set_delay_direct_mix",
    "get_delay_time", "set_delay_time",
    "get_delay_high_cut", "set_delay_high_cut",
    # delay 2
    "delay2_on", "delay2_off", "delay2_is_on",
    "get_delay2_type", "set_delay2_type",
    "get_delay2_time", "set_delay2_time",
    "get_delay2_feedback", "set_delay2_feedback",
    "get_delay2_high_cut", "set_delay2_high_cut",
    "get_delay2_level", "set_delay2_level",
    "get_delay2_direct_mix", "set_delay2_direct_mix",
    # noise suppressor
    "noise_gate_on", "noise_gate_off", "noise_gate_is_on",
    "get_noise_threshold", "set_noise_threshold",
    "get_noise_release", "set_noise_release",
    # reverb
    "reverb_on", "reverb_off", "reverb_is_on",
    "get_reverb_type", "set_reverb_type", "list_reverb_types",
    "get_reverb_time", "set_reverb_time",
    "get_reverb_level", "set_reverb_level",
    "get_reverb_direct_mix", "set_reverb_direct_mix",
    # wah
    "wah_on", "wah_off", "wah_is_on", "get_wah", "set_wah",
    "cry_wah", "use_wah", "sweep_wah", "wah_wah",
    "get_wah_type", "set_wah_type", "list_wah_types",
    "get_pedal_type", "set_pedal_type",
    "get_wah_level", "set_wah_level",
    "get_wah_direct_mix", "set_wah_direct_mix",
    "get_wah_pedal_min", "set_wah_pedal_min",
    "get_wah_pedal_max", "set_wah_pedal_max",
    # eq
    "get_eq_band", "set_eq_band", "get_eq", "set_eq", "reset_eq", "EQ_BANDS",
    # effect parameters
    "use_effect",
    "get_phaser_rate", "set_phaser_rate", "get_phaser_depth", "set_phaser_depth",
    "get_phaser_manual", "set_phaser_manual",
    "get_phaser_resonance", "set_phaser_resonance",
    "get_phaser_level", "set_phaser_level",
    "get_phaser_type", "set_phaser_type",
    "get_flanger_rate", "set_flanger_rate", "get_flanger_depth", "set_flanger_depth",
    "get_flanger_manual", "set_flanger_manual",
    "get_flanger_resonance", "set_flanger_resonance",
    "get_flanger_level", "set_flanger_level",
    "get_tremolo_rate", "set_tremolo_rate", "get_tremolo_depth", "set_tremolo_depth",
    "get_tremolo_waveshape", "set_tremolo_waveshape",
    "get_tremolo_level", "set_tremolo_level",
    "get_vibrato_rate", "set_vibrato_rate", "get_vibrato_depth", "set_vibrato_depth",
    "get_vibrato_level", "set_vibrato_level",
    "get_uni_v_rate", "set_uni_v_rate", "get_uni_v_depth", "set_uni_v_depth",
    "get_uni_v_level", "set_uni_v_level",
    # patches
    "save_to_patch", "read_patch_parameter", "get_patch_names",
    # channels
    "select_channel", "list_channels", "get_patch_name",
    "switch_effect", "send_cc", "set_expression", "list_control_changes",
    # LEDs
    "get_led", "set_led", "get_leds", "set_leds",
    "list_led_colours", "LED_SECTIONS",
    # overview
    "show_settings",
]

from contextlib import contextmanager

from katana_amp.katana import (
    AMP_TYPES,
    CHANNELS,
    CONTROL_CHANGES,
    LED_COLOURS,
    WIDE_PARAMETERS,
    BOOST_TYPES,
    DELAY_TYPES,
    EFFECT_TYPES,
    PARAMETERS,
    PEDAL_TYPES,
    REVERB_TYPES,
    WAH_TYPES,
    Katana,
    KatanaError,
)

# There is only ever one amp, so the helpers share a single connection that
# is opened on first use and reused from then on. You never have to pass it
# around, but every helper still takes amp= if you want to be explicit.
_amp = None


def connect(port_name=None):
    """Open the shared connection, or return the one already open."""
    global _amp
    if _amp is None:
        _amp = Katana(port_name)
    return _amp


def disconnect():
    """Close the shared connection. The next helper call reopens it."""
    global _amp
    if _amp is not None:
        _amp.close()
        _amp = None


@contextmanager
def _connection(amp):
    """Use the caller's amp if given, otherwise the shared one."""
    yield amp if amp is not None else connect()


def amp_session():
    """An explicit `with` block, for when you want your own connection."""
    return Katana()


# --- Anything by name ------------------------------------------------------

def get_parameter(name, amp=None):
    """Read any parameter by name. See list_parameters()."""
    with _connection(amp) as a:
        return a.get_parameter(name)


def set_parameter(name, value, amp=None):
    """Set any parameter by name, for controls with no dedicated helper."""
    with _connection(amp) as a:
        a.set_parameter(name, value)
        return value


def get_wide_parameter(name, amp=None):
    """Read a two-byte parameter, e.g. delay time in ms."""
    with _connection(amp) as a:
        return a.get_wide_parameter(name)


def set_wide_parameter(name, value, amp=None):
    """Set a two-byte parameter, e.g. delay time in ms."""
    with _connection(amp) as a:
        a.set_wide_parameter(name, value)
        return value


def _make_wide(name):
    """Build a get/set pair for a two-byte parameter."""

    def getter(amp=None):
        return get_wide_parameter(name, amp=amp)

    def setter(value, amp=None):
        return set_wide_parameter(name, value, amp=amp)

    low, high = WIDE_PARAMETERS[name][1], WIDE_PARAMETERS[name][2]
    getter.__doc__ = f"Return {name} ({low}-{high})."
    setter.__doc__ = f"Set {name} ({low}-{high})."
    return getter, setter


def list_parameters():
    """Return {name: (low, high)} for every controllable parameter."""
    listing = {name: (low, high) for name, (_, low, high) in PARAMETERS.items()}
    listing.update(
        {name: (low, high) for name, (_, low, high) in WIDE_PARAMETERS.items()}
    )
    return listing


def _make(name):
    """Build a get/set pair for a plain numeric parameter."""

    def getter(amp=None):
        return get_parameter(name, amp=amp)

    def setter(value, amp=None):
        return set_parameter(name, value, amp=amp)

    low, high = PARAMETERS[name][1], PARAMETERS[name][2]
    getter.__name__, setter.__name__ = f"get_{name}", f"set_{name}"
    getter.__doc__ = f"Return {name} ({low}-{high})."
    setter.__doc__ = f"Set {name} ({low}-{high})."
    return getter, setter


def _switch(name, label):
    """Build on()/off()/is_on() for a 0/1 switch."""

    def on(amp=None):
        return set_parameter(name, 1, amp=amp)

    def off(amp=None):
        return set_parameter(name, 0, amp=amp)

    def state(amp=None):
        return bool(get_parameter(name, amp=amp))

    on.__doc__ = f"Switch {label} on."
    off.__doc__ = f"Switch {label} off."
    state.__doc__ = f"Return True if {label} is on."
    return on, off, state


def _normalise(text):
    return "".join(c for c in text.lower() if c.isalnum())


def _match(name, table, what):
    """Resolve a name to its number in `table`, matching loosely."""
    wanted = _normalise(name)

    for number, label in table.items():
        if _normalise(label) == wanted:
            return number

    partial = [n for n, label in table.items() if wanted in _normalise(label)]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        options = ", ".join(sorted(table[n] for n in partial))
        raise KatanaError(f"{name!r} matches several {what}s: {options}")

    known = ", ".join(table[n] for n in sorted(table))
    raise KatanaError(f"No {what} called {name!r}. Known {what}s: {known}")


def _typed(name, table, what):
    """Build a get/set pair for a parameter whose values have names."""

    def getter(amp=None):
        value = get_parameter(name, amp=amp)
        return value, table.get(value, f"Unknown ({value})")

    def setter(choice, amp=None):
        if isinstance(choice, str):
            choice = _match(choice, table, what)
        set_parameter(name, choice, amp=amp)
        return choice, table.get(choice, str(choice))

    getter.__doc__ = f"Return the current {what} as (number, name)."
    setter.__doc__ = f"Set the {what}, by number or name (names match loosely)."
    return getter, setter


# --- Amp -------------------------------------------------------------------

get_gain, set_gain = _make("gain")
get_volume, set_volume = _make("volume")
get_bass, set_bass = _make("bass")
get_middle, set_middle = _make("middle")
get_treble, set_treble = _make("treble")
get_presence, set_presence = _make("presence")
get_amp_type, set_amp_type = _typed("amp_type", AMP_TYPES, "amp")
bright_on, bright_off, bright_is_on = _switch("bright", "the bright switch")


def get_knob_volume(amp=None):
    """Return the physical volume knob position. Read-only over MIDI."""
    return get_parameter("knob_volume", amp=amp)


def set_tone(bass=None, middle=None, treble=None, presence=None, amp=None):
    """Set any combination of tone controls in one go."""
    with _connection(amp) as a:
        for name, value in (
            ("bass", bass), ("middle", middle),
            ("treble", treble), ("presence", presence),
        ):
            if value is not None:
                a.set_parameter(name, value)


# --- Boost / overdrive -----------------------------------------------------

boost_on, boost_off, boost_is_on = _switch("boost_switch", "the boost")
get_boost_type, set_boost_type = _typed("boost_type", BOOST_TYPES, "boost")
get_boost_drive, set_boost_drive = _make("boost_drive")
get_boost_bottom, set_boost_bottom = _make("boost_bottom")
get_boost_tone, set_boost_tone = _make("boost_tone")
get_boost_level, set_boost_level = _make("boost_level")
get_boost_solo_level, set_boost_solo_level = _make("boost_solo_level")
get_boost_direct_mix, set_boost_direct_mix = _make("boost_direct_mix")
boost_solo_on, boost_solo_off, boost_solo_is_on = _switch(
    "boost_solo_switch", "the boost solo"
)


# --- EQ --------------------------------------------------------------------

eq_on, eq_off, eq_is_on = _switch("eq_switch", "the EQ")
get_eq_type, set_eq_type = _make("eq_type")


# --- Effect slots ----------------------------------------------------------

fx1_on, fx1_off, fx1_is_on = _switch("fx1_switch", "effect slot 1")
fx2_on, fx2_off, fx2_is_on = _switch("fx2_switch", "effect slot 2")
get_fx1_type, set_fx1_type = _typed("fx1_type", EFFECT_TYPES, "effect")
get_fx2_type, set_fx2_type = _typed("fx2_type", EFFECT_TYPES, "effect")


def list_amp_types():
    """Return {number: name} for all 28 amp models."""
    return dict(AMP_TYPES)


def list_boost_types():
    """Return {number: name} for the boost/overdrive types."""
    return dict(BOOST_TYPES)


def list_effect_types():
    """Return {number: name} for the FX slot effects."""
    return dict(EFFECT_TYPES)


# --- Delay -----------------------------------------------------------------

delay_on, delay_off, delay_is_on = _switch("delay_switch", "the delay")
get_delay_type, set_delay_type = _typed("delay_type", DELAY_TYPES, "delay")
get_delay_feedback, set_delay_feedback = _make("delay_feedback")
get_delay_level, set_delay_level = _make("delay_level")
get_delay_direct_mix, set_delay_direct_mix = _make("delay_direct_mix")


get_delay_time, set_delay_time = _make_wide("delay_time")
get_delay_high_cut, set_delay_high_cut = _make("delay_high_cut")


def list_delay_types():
    """Return {number: name} for the delay types."""
    return dict(DELAY_TYPES)


# --- Delay 2 ---------------------------------------------------------------
#
# A second, independent delay engine with the same controls as delay 1.

delay2_on, delay2_off, delay2_is_on = _switch("delay2_switch", "the second delay")
get_delay2_type, set_delay2_type = _typed("delay2_type", DELAY_TYPES, "delay")
get_delay2_time, set_delay2_time = _make_wide("delay2_time")
get_delay2_feedback, set_delay2_feedback = _make("delay2_feedback")
get_delay2_high_cut, set_delay2_high_cut = _make("delay2_high_cut")
get_delay2_level, set_delay2_level = _make("delay2_level")
get_delay2_direct_mix, set_delay2_direct_mix = _make("delay2_direct_mix")


# --- Noise suppressor ------------------------------------------------------
#
# Gates the hiss between notes. Raise the threshold until the noise stops;
# too high and it starts clipping the tail off what you play.

noise_gate_on, noise_gate_off, noise_gate_is_on = _switch(
    "noise_suppressor_switch", "the noise suppressor"
)
get_noise_threshold, set_noise_threshold = _make("noise_suppressor_threshold")
get_noise_release, set_noise_release = _make("noise_suppressor_release")


# --- Reverb ----------------------------------------------------------------

reverb_on, reverb_off, reverb_is_on = _switch("reverb_switch", "the reverb")
get_reverb_type, set_reverb_type = _typed("reverb_type", REVERB_TYPES, "reverb")
get_reverb_time, set_reverb_time = _make("reverb_time")
get_reverb_level, set_reverb_level = _make("reverb_level")
get_reverb_direct_mix, set_reverb_direct_mix = _make("reverb_direct_mix")


def list_reverb_types():
    """Return {number: name} for the reverb types."""
    return dict(REVERB_TYPES)


# --- Wah -------------------------------------------------------------------
#
# The wah lives on the amp's pedal section, separate from the FX slots.
# "Switching it on" means turning that pedal section on; the sound then
# depends on the voicing (Cry Wah, Vo Wah, ...) and the treadle position.

wah_on, wah_off, wah_is_on = _switch("pedal_switch", "the pedal wah")
get_wah_type, set_wah_type = _typed("wah_type", WAH_TYPES, "wah")
get_pedal_type, set_pedal_type = _typed("pedal_type", PEDAL_TYPES, "pedal mode")
get_wah_level, set_wah_level = _make("wah_level")
get_wah_direct_mix, set_wah_direct_mix = _make("wah_direct_mix")
get_wah_pedal_min, set_wah_pedal_min = _make("wah_pedal_min")
get_wah_pedal_max, set_wah_pedal_max = _make("wah_pedal_max")


def list_wah_types():
    """Return {number: name} for the wah voicings."""
    return dict(WAH_TYPES)


def get_wah(amp=None):
    """Return (is_on, voicing_name, pedal_position)."""
    with _connection(amp) as a:
        on = bool(a.get_parameter("pedal_switch"))
        voicing = a.get_parameter("wah_type")
        return on, WAH_TYPES.get(voicing, str(voicing)), a.get_parameter("wah_position")


def set_wah(position, amp=None):
    """Move the wah treadle, 0 (heel) to 100 (toe).

    Parking it at one position just sets the filter. Sweeping is what makes
    the wah sound - see sweep_wah().
    """
    return set_parameter("wah_position", position, amp=amp)


def cry_wah(amp=None):
    """Load the Cry Wah voicing and switch the pedal on."""
    return use_wah("Cry Wah", amp=amp)


def use_wah(voicing="Cry Wah", amp=None):
    """Switch the pedal section to wah, load `voicing`, and turn it on.

    This is the one-call way to actually get a wah, because the pedal
    section also does pedal-bend and has to be pointed at wah first.
    """
    with _connection(amp) as a:
        a.set_parameter("pedal_type", 0)
        number = voicing
        if isinstance(number, str):
            number = _match(number, WAH_TYPES, "wah")
        a.set_parameter("wah_type", number)
        a.set_parameter("pedal_switch", 1)
        return number, WAH_TYPES.get(number, str(number))


def sweep_wah(start=0, end=100, steps=50, delay=0.1, amp=None):
    """Sweep the treadle from `start` to `end` so you can hear it move.

    Switches the pedal section on first. Reuses one connection so the
    steps stay smooth.
    """
    import time

    with _connection(amp) as a:
        a.set_parameter("pedal_switch", 1)
        steps = max(steps, 2)
        for i in range(steps):
            position = round(start + (end - start) * i / (steps - 1))
            a.set_parameter("wah_position", position)
            time.sleep(delay)
        return end


def wah_wah(cycles=3, amp=None):
    """Rock the treadle up and down `cycles` times. The classic sound."""
    with _connection(amp) as a:
        for _ in range(cycles):
            sweep_wah(0, 100, steps=25, delay=0.04, amp=a)
            sweep_wah(100, 0, steps=25, delay=0.04, amp=a)


# --- Graphic EQ ------------------------------------------------------------
#
# Ten bands, each -24 to +24 dB. The amp stores 0-48 with 24 as flat; these
# helpers take dB so you do not have to think about the offset.

EQ_BANDS = ("31hz", "62hz", "125hz", "250hz", "500hz",
            "1khz", "2khz", "4khz", "8khz", "16khz")

_EQ_CENTRE = 24


def get_eq_band(band, amp=None):
    """Return one graphic EQ band in dB (-24 to +24). Band e.g. "1khz"."""
    return get_parameter(_eq_name(band), amp=amp) - _EQ_CENTRE


def set_eq_band(band, decibels, amp=None):
    """Set one graphic EQ band in dB, -24 to +24. Band e.g. "1khz"."""
    if not -_EQ_CENTRE <= decibels <= _EQ_CENTRE:
        raise KatanaError(
            f"EQ gain must be -{_EQ_CENTRE} to +{_EQ_CENTRE} dB, got {decibels}"
        )
    set_parameter(_eq_name(band), decibels + _EQ_CENTRE, amp=amp)
    return decibels


def get_eq(amp=None):
    """Return {band: dB} for all ten bands."""
    with _connection(amp) as a:
        return {b: get_eq_band(b, amp=a) for b in EQ_BANDS}


def set_eq(amp=None, **bands):
    """Set several bands at once, in dB.

        set_eq(**{"125hz": 3, "1khz": -2})
    """
    with _connection(amp) as a:
        for band, decibels in bands.items():
            set_eq_band(band, decibels, amp=a)


def reset_eq(amp=None):
    """Set every graphic EQ band flat."""
    with _connection(amp) as a:
        for band in EQ_BANDS:
            set_eq_band(band, 0, amp=a)


def _eq_name(band):
    name = f"eq_band_{str(band).lower()}"
    if name not in PARAMETERS:
        raise KatanaError(f"No EQ band {band!r}. Bands: {', '.join(EQ_BANDS)}")
    return name


# --- Effect parameters -----------------------------------------------------
#
# Each effect keeps its own settings whatever the slot is switched to, so
# you can dial one in before selecting it.

get_phaser_rate, set_phaser_rate = _make("phaser_rate")
get_phaser_depth, set_phaser_depth = _make("phaser_depth")
get_phaser_manual, set_phaser_manual = _make("phaser_manual")
get_phaser_resonance, set_phaser_resonance = _make("phaser_resonance")
get_phaser_level, set_phaser_level = _make("phaser_level")
get_phaser_type, set_phaser_type = _make("phaser_type")

get_flanger_rate, set_flanger_rate = _make("flanger_rate")
get_flanger_depth, set_flanger_depth = _make("flanger_depth")
get_flanger_manual, set_flanger_manual = _make("flanger_manual")
get_flanger_resonance, set_flanger_resonance = _make("flanger_resonance")
get_flanger_level, set_flanger_level = _make("flanger_level")

get_tremolo_rate, set_tremolo_rate = _make("tremolo_rate")
get_tremolo_depth, set_tremolo_depth = _make("tremolo_depth")
get_tremolo_waveshape, set_tremolo_waveshape = _make("tremolo_waveshape")
get_tremolo_level, set_tremolo_level = _make("tremolo_level")

get_vibrato_rate, set_vibrato_rate = _make("vibrato_rate")
get_vibrato_depth, set_vibrato_depth = _make("vibrato_depth")
get_vibrato_level, set_vibrato_level = _make("vibrato_level")

get_uni_v_rate, set_uni_v_rate = _make("uni_v_rate")
get_uni_v_depth, set_uni_v_depth = _make("uni_v_depth")
get_uni_v_level, set_uni_v_level = _make("uni_v_level")


# The rest of the effect blocks, generated from PARAMETERS so every one
# gets a get_/set_ pair without hand-writing them.
_EFFECT_PREFIXES = (
    "t_wah", "auto_wah", "comp", "limiter", "guitar_sim", "wave_synth",
    "octave", "rotary", "slicer", "ring_mod", "humanizer",
)

for _name in PARAMETERS:
    if _name.startswith(_EFFECT_PREFIXES) and f"get_{_name}" not in globals():
        globals()[f"get_{_name}"], globals()[f"set_{_name}"] = _make(_name)
        __all__.extend([f"get_{_name}", f"set_{_name}"])
del _name


def use_effect(slot, effect, amp=None):
    """Point an FX slot at an effect and switch it on. Slot is 1 or 2.

        use_effect(1, "Phaser")
    """
    if slot not in (1, 2):
        raise KatanaError(f"FX slot must be 1 or 2, got {slot}")
    with _connection(amp) as a:
        number = effect
        if isinstance(number, str):
            number = _match(number, EFFECT_TYPES, "effect")
        a.set_parameter(f"fx{slot}_type", number)
        a.set_parameter(f"fx{slot}_switch", 1)
        return number, EFFECT_TYPES.get(number, str(number))


# --- Patch memory ----------------------------------------------------------
#
# The eight stored sounds behind the CH buttons. Editing these does not
# disturb what is playing; select_channel() then loads one.

def save_to_patch(patch, amp=None):
    """Copy the current live sound into stored patch 1-9.

    Patch 1-4 are BANK A CH1-4, 6-9 are BANK B CH1-4.
    """
    with _connection(amp) as a:
        return a.copy_live_to_patch(patch)


def read_patch_parameter(patch, name, amp=None):
    """Read one named parameter from a stored patch without loading it."""
    address, _, _ = PARAMETERS[name] if name in PARAMETERS else (None, 0, 0)
    if address is None:
        raise KatanaError(f"Unknown parameter {name!r}")
    with _connection(amp) as a:
        return a.read_patch(patch, address - 0x60000000, 1)[0]


def get_patch_names(amp=None):
    """Return {patch_number: name} for all nine stored patches."""
    names = {}
    with _connection(amp) as a:
        for patch in range(1, 10):
            raw = a.read_patch(patch, 0x00, 16)
            names[patch] = "".join(chr(b) for b in raw if 0x20 <= b < 0x7F).strip()
    return names


# --- Channels (tone settings) ----------------------------------------------
#
# The amp's four channels per bank, plus PANEL. Switched with Program
# Change, which is what the manual documents - this is the real way to
# change channel, and the panel LEDs follow.

def select_channel(channel, amp=None):
    """Switch channel: "a1".."a4", "panel", "b1".."b4", or a number 1-9."""
    with _connection(amp) as a:
        return a.select_channel(channel)


def list_channels():
    """Return {name: program_number} for the selectable channels."""
    return dict(CHANNELS)


def get_patch_name(amp=None):
    """Return the name of the patch currently loaded."""
    with _connection(amp) as a:
        return a.read_patch_name()


# --- Effect switching by CC ------------------------------------------------
#
# The manual's documented way to toggle effect blocks. Equivalent to the
# *_on/*_off helpers, but uses the same messages a footswitch would.

def switch_effect(name, on, amp=None):
    """Toggle an effect block by CC: boost, mod, fx, delay, reverb, effect_loop."""
    with _connection(amp) as a:
        return a.switch_effect(name, on)


def send_cc(control, value, amp=None):
    """Send a raw Control Change to the amp."""
    with _connection(amp) as a:
        a.send_control_change(control, value)
        return value


def set_expression(value, amp=None):
    """Move the external expression pedal (CC 82), 0-127."""
    return send_cc(82, value, amp=amp)


def list_control_changes():
    """Return {effect: cc_number} for the documented CC messages."""
    return dict(CONTROL_CHANGES)


# --- Channel / colour state ------------------------------------------------
#
# READ-ONLY IN PRACTICE. These report which colour channel each section is
# on, and the values do store, but on a MkII writing them changes nothing -
# not the panel LEDs, not the sound. Tested on hardware. Use get_led/get_leds
# to see the state; treat set_led/set_leds as non-functional for now.
#
# Changing the actual colour channel most likely needs the CC messages the
# amp documents for the footswitch (CC 16-18), not a SysEx write here.

LED_SECTIONS = ("boost", "mod", "fx", "delay", "reverb")


def get_led(section, amp=None):
    """Return (number, colour_name) for one section's colour channel.

    `section` is one of boost, mod, fx, delay, reverb.
    """
    value = get_parameter(_led_name(section), amp=amp)
    return value, LED_COLOURS.get(value, str(value))


def set_led(section, colour, amp=None):
    """Store a colour channel value. DOES NOT change the panel or the sound.

    The write is accepted and reads back, but has no audible or visible
    effect on a MkII. Kept for completeness; prefer get_led() for reading.
    """
    if isinstance(colour, str):
        colour = _match(colour, LED_COLOURS, "colour")
    set_parameter(_led_name(section), colour, amp=amp)
    return colour, LED_COLOURS.get(colour, str(colour))


def get_leds(amp=None):
    """Return {section: colour_name} for all five sections."""
    with _connection(amp) as a:
        return {s: get_led(s, amp=a)[1] for s in LED_SECTIONS}


def set_leds(colour, amp=None):
    """Store the same colour value for every section. Has no visible effect."""
    with _connection(amp) as a:
        for section in LED_SECTIONS:
            set_led(section, colour, amp=a)


def _led_name(section):
    name = f"led_{section}"
    if name not in PARAMETERS:
        raise KatanaError(
            f"No LED section {section!r}. Sections: {', '.join(LED_SECTIONS)}"
        )
    return name


def list_led_colours():
    """Return {number: name} for the colour channels."""
    return dict(LED_COLOURS)


# --- Overview --------------------------------------------------------------

def show_settings(amp=None):
    """Print everything the amp is currently set to. Returns a dict."""
    with _connection(amp) as a:
        panel = a.read_panel()
        # Only the parameters this overview prints. Reading all of them
        # would be slow, and effect blocks do not answer unless their
        # effect is the one currently loaded in the slot.
        wanted = (
            "amp_type", "gain", "volume", "bass", "middle", "treble",
            "presence", "boost_switch", "boost_type", "boost_drive",
            "boost_level", "fx1_switch", "fx1_type", "fx2_switch",
            "fx2_type", "delay_switch", "delay_type", "delay_feedback",
            "delay_level", "delay2_switch", "delay2_type",
            "delay2_feedback", "delay2_level", "reverb_switch",
            "reverb_type", "reverb_time", "reverb_level", "pedal_switch",
            "pedal_type", "wah_type", "wah_position", "eq_switch",
            "noise_suppressor_switch", "noise_suppressor_threshold",
            "noise_suppressor_release",
        ) + tuple(f"led_{section}" for section in LED_SECTIONS)

        values = {}
        for name in wanted:
            try:
                values[name] = a.get_parameter(name)
            except KatanaError:
                values[name] = 0
        for name in ("delay_time", "delay2_time"):
            try:
                values[name] = a.get_wide_parameter(name)
            except KatanaError:
                values[name] = 0

    def named(table, key):
        value = values[key]
        return table.get(value, f"type {value}")

    print(f"Patch:      {panel['patch_name'] or '(unnamed)'}")
    print(f"Amp:        {named(AMP_TYPES, 'amp_type')}")
    print(f"  gain {values['gain']}  volume {values['volume']}  "
          f"bass {values['bass']}  middle {values['middle']}  "
          f"treble {values['treble']}  presence {values['presence']}")

    state = lambda key: "on " if values[key] else "off"
    print(f"Boost:      {state('boost_switch')}  {named(BOOST_TYPES, 'boost_type')}"
          f"  drive {values['boost_drive']}  level {values['boost_level']}")
    print(f"FX1:        {state('fx1_switch')}  {named(EFFECT_TYPES, 'fx1_type')}")
    print(f"FX2:        {state('fx2_switch')}  {named(EFFECT_TYPES, 'fx2_type')}")
    print(f"Delay:      {state('delay_switch')}  {named(DELAY_TYPES, 'delay_type')}"
          f"  {values['delay_time']}ms  feedback {values['delay_feedback']}"
          f"  level {values['delay_level']}")
    print(f"Delay 2:    {state('delay2_switch')}  {named(DELAY_TYPES, 'delay2_type')}"
          f"  {values['delay2_time']}ms  feedback {values['delay2_feedback']}"
          f"  level {values['delay2_level']}")
    print(f"Reverb:     {state('reverb_switch')}  {named(REVERB_TYPES, 'reverb_type')}"
          f"  time {values['reverb_time']}  level {values['reverb_level']}")
    print(f"Pedal/wah:  {state('pedal_switch')}  {named(WAH_TYPES, 'wah_type')}"
          f"  ({named(PEDAL_TYPES, 'pedal_type')})  position {values['wah_position']}")
    print(f"EQ:         {state('eq_switch')}")
    leds = "  ".join(
        f"{s} {LED_COLOURS.get(values['led_' + s], values['led_' + s])}"
        for s in LED_SECTIONS
    )
    print(f"Channels:   {leds}")
    print(f"Noise gate: {state('noise_suppressor_switch')}"
          f"  threshold {values['noise_suppressor_threshold']}"
          f"  release {values['noise_suppressor_release']}")
    return values
