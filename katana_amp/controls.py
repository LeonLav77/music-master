"""The one shared connection to the amp, and the operations built on it.

There is only one amp, so everything shares a single connection that opens
on first use. Nothing to pass around, nothing to close:

    from katana_amp.controls import get_parameter, set_parameter
    from katana_amp.params import Param

    set_parameter(Param.GAIN, 75)
    get_parameter(Param.REVERB_LEVEL)
    list(Param)                       # every setting there is

Values are checked against the setting's range before anything is sent;
a bad one raises KatanaError rather than reaching the amp.
"""

import contextlib
import time

from katana_amp.katana import NAME_LENGTH, Katana, decode_name
from katana_amp.params import Param

# There is only ever one amp, so it gets a single connection that is opened
# on first use and reused from then on.
_amp = None


def connect(port_name=None):
    """Open the shared connection, or return the one already open.

    A connection that fails to open leaves nothing cached, so the next call
    tries again from scratch rather than handing back a half-dead object.
    """
    global _amp
    if _amp is None:
        _amp = Katana(port_name)
    return _amp


def disconnect():
    """Close the shared connection. The next call reopens it."""
    global _amp
    if _amp is not None:
        # A port whose device has been unplugged can raise on close; the
        # point is to stop using it either way.
        with contextlib.suppress(Exception):
            _amp.close()
        _amp = None


def is_connected():
    """True if a connection is currently open."""
    return _amp is not None


# --- Settings --------------------------------------------------------------

def get_parameter(param):
    """Read one setting (a Param), in real units: EQ in dB, delay in ms."""
    return connect().get_parameter(param)


def set_parameter(param, value):
    """Write one setting (a Param), in real units."""
    connect().set_parameter(param, value)
    return value


# --- Wah -------------------------------------------------------------------

def sweep_wah(start=0, end=100, steps=50, delay=0.1):
    """Sweep the treadle from `start` to `end` so you can hear it move.

    Switches the pedal section on first. Reuses one connection so the
    steps stay smooth.
    """
    amp = connect()
    amp.set_parameter(Param.PEDAL_SWITCH, 1)
    steps = max(steps, 2)
    for i in range(steps):
        position = round(start + (end - start) * i / (steps - 1))
        amp.set_parameter(Param.WAH_POSITION, position)
        time.sleep(delay)
    return end


def rock_wah(intervals=4, low=0, high=50, seconds=2.3, bounce=True):
    """Rock the treadle `intervals` times, each one taking `seconds`.

    "4 intervals of 0 to 50 in 2.3 seconds" is rock_wah(4, 0, 50, 2.3):
    four sweeps low->high->low, 2.3 s each, 9.2 s in total.

    With bounce=False the pedal only sweeps up and snaps back, which is
    sharper and more rhythmic.

    Step count is derived from the duration rather than taken as an
    argument: the amp accepts roughly 40 parameter writes a second before
    the MIDI port becomes the bottleneck and the motion turns lumpy, so
    the rate is capped there and the step size grows for slow sweeps
    instead of flooding the port.
    """
    intervals = max(1, int(intervals))
    seconds = max(0.05, float(seconds))
    low, high = int(low), int(high)

    # Per leg: half the interval when bouncing, all of it when snapping back.
    legs = 2 if bounce else 1
    leg_seconds = seconds / legs

    # ~40 Hz ceiling, and never fewer than 2 points or it is a jump, not a sweep.
    steps = max(2, min(int(leg_seconds * 40), 200))
    delay = leg_seconds / steps

    amp = connect()
    amp.set_parameter(Param.PEDAL_SWITCH, 1)
    for _ in range(intervals):
        for i in range(steps):
            position = round(low + (high - low) * i / (steps - 1))
            amp.set_parameter(Param.WAH_POSITION, position)
            time.sleep(delay)
        if bounce:
            for i in range(steps):
                position = round(high + (low - high) * i / (steps - 1))
                amp.set_parameter(Param.WAH_POSITION, position)
                time.sleep(delay)
        else:
            amp.set_parameter(Param.WAH_POSITION, low)
    return low


# --- Channels and stored patches -------------------------------------------
#
# The amp's four channels per bank, plus PANEL. Switched with Program
# Change, which is what the manual documents; the panel LEDs follow.

def select_channel(channel):
    """Switch channel: "a1".."a4", "panel", "b1".."b4", or a number 1-9."""
    return connect().select_channel(channel)


def save_to_patch(patch):
    """Copy the current live sound into stored patch 1-9. Overwrites it.

    Patch 1-4 are BANK A CH1-4, 6-9 are BANK B CH1-4.
    """
    return connect().copy_live_to_patch(patch)


def get_patch_names():
    """Return {patch_number: name} for all nine stored patches."""
    amp = connect()
    return {
        patch: decode_name(amp.read_patch(patch, 0x00, NAME_LENGTH))
        for patch in range(1, 10)
    }


# --- Footswitch messages ---------------------------------------------------

def send_cc(control, value):
    """Send a raw Control Change, as a footswitch would."""
    connect().send_control_change(control, value)
    return value
