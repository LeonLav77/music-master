"""Read BOSS Tone Studio .tsl patch files.

    from katana_amp.tsl import load

    bank = load("my tones.tsl")
    for patch in bank:
        print(patch.name, patch.get(Param.GAIN))

    bank[0].apply(connect())   # load the first patch into the amp

A .tsl file is JSON holding one or more patches, each a set of named byte
blocks ("UserPatch%Patch_0", "UserPatch%Fx(1)", ...). Those blocks are the
same bytes the amp keeps in memory, so a patch can be read here and sent
straight to the amp.

A block is stored as a plain run of bytes, but amp addresses skip from
xx7F to the next xx00 (each address byte only counts to 127). So byte 128
of the Fx(1) block lives at 0x200, not 0x180 - see katana.advance().
"""

import json
import time

from katana_amp.katana import LIVE_BASE, PATCH_BLOCKS, KatanaError, advance, decode_name
from katana_amp.param import Param


class Patch:
    """One patch from a .tsl file."""

    def __init__(self, blocks, memo=""):
        self.blocks = blocks
        self.memo = memo

    @property
    def name(self):
        raw = self.blocks.get("UserPatch%PatchName", [])
        return decode_name(raw)

    def memory(self):
        """Return {address: byte} for everything this patch defines, at
        the addresses the amp's live area would hold them."""
        image = {}
        for block, (offset, _) in PATCH_BLOCKS.items():
            for index, byte in enumerate(self.blocks.get(f"UserPatch%{block}", [])):
                image[advance(LIVE_BASE + offset, index)] = byte
        return image

    def get(self, param):
        """One setting (a Param) as the amp would report it, or None if the
        patch does not define it."""
        return self.settings().get(param)

    def settings(self):
        """Return {Param: value} for every setting the patch defines."""
        image = self.memory()
        found = {}
        for param in Param:
            data = [image.get(advance(param.address(), index)) for index in range(param.size())]
            if None not in data:
                found[param] = param.decode(data)
        return found

    def apply(self, amp, settle=0.02):
        """Load this patch by setting each named parameter individually.

        This walks the parameters the file defines and writes each one
        through the normal parameter path, so every value is range-checked
        on the way in.

        Only parameters this project has mapped are set; anything else in
        the file is ignored. Read-only ones (LEDs, knob positions) are
        skipped too - the amp ignores writes to them. Returns (applied,
        skipped).
        """
        values = {param: value for param, value in self.settings().items() if param.is_writable()}

        # Effect switches last, so a section is configured before it is
        # switched on and you never hear a half-set effect.
        switches = {param: value for param, value in values.items() if param.endswith("_switch")}
        rest = {param: value for param, value in values.items() if not param.endswith("_switch")}

        applied = 0
        skipped = []
        for group in (rest, switches):
            for param, value in sorted(group.items()):
                try:
                    amp.set_parameter(param, value)
                    applied += 1
                except KatanaError:
                    skipped.append(param.value)
                time.sleep(settle)

        return applied, skipped

    def __repr__(self):
        return f"<Patch {self.name!r}>"


def load(path):
    """Load a .tsl file and return its patches as a list."""
    with open(path) as handle:
        document = json.load(handle)

    device = document.get("device", "")
    if "KATANA" not in device.upper():
        raise KatanaError(f"{path} is for a {device!r}, not a Katana")

    patches = []
    for group in document.get("data", []):
        for entry in group:
            blocks = {
                key: [int(byte, 16) for byte in value]
                for key, value in entry.get("paramSet", {}).items()
            }
            patches.append(Patch(blocks, entry.get("memo", "")))
    return patches


def describe(path):
    """Print a summary of every patch in a .tsl file."""
    for index, patch in enumerate(load(path), 1):
        amp_type = patch.get(Param.AMP_TYPE)
        print(
            f"{index}. {patch.name:20s} "
            f"{Param.AMP_TYPE.options().get(amp_type, f'amp {amp_type}'):16s} "
            f"gain {patch.get(Param.GAIN)}  vol {patch.get(Param.VOLUME)}"
        )
