"""What sort of control a setting is.

    from katana_amp.kind import Kind

    Param.GAIN.kind()      Kind.RANGE
"""

from enum import StrEnum


class Kind(StrEnum):
    """What sort of control a setting is - and what the UI draws for it."""

    RANGE = "range"    # a knob
    TOGGLE = "toggle"  # a switch
    ENUM = "enum"      # a dropdown
