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
