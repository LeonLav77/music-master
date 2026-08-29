"""Control a BOSS Katana MkII amplifier over USB MIDI.

    from katana_amp import controls

    controls.set_gain(75)
    controls.set_amp_type("5150 Drive")

`katana` holds the protocol and the address map, `controls` the friendly
helpers, and `tsl` reads Boss Tone Studio patch files.
"""

from katana_amp.katana import Katana, KatanaError, find_ports

__all__ = ["Katana", "KatanaError", "find_ports"]
