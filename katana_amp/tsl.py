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
"""

import json
import time

from katana_amp.katana import LIVE_BASE, KatanaError, decode_name
from katana_amp.param import Param

# Which memory offset each named block starts at, relative to the base of a
# patch. Derived by matching the block contents against the amp's own layout.
BLOCK_OFFSETS = {
    "UserPatch%PatchName": 0x000,
    "UserPatch%Patch_0": 0x010,
    "UserPatch%Fx(1)": 0x100,
    "UserPatch%Fx(2)": 0x300,
    "UserPatch%Delay(1)": 0x500,
    "UserPatch%Delay(2)": 0x520,
    "UserPatch%Patch_1": 0x540,
    "UserPatch%Patch_2": 0x600,
    "UserPatch%Status": 0x650,
    "UserPatch%KnobAsgn": 0x700,
}


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
        """Return {offset: byte} for everything this patch defines."""
        image = {}
        for block, start in BLOCK_OFFSETS.items():
            for index, byte in enumerate(self.blocks.get(block, [])):
                image[start + index] = byte
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
            start = param.address() - LIVE_BASE
            data = [image.get(start + index) for index in range(param.size())]
            if None not in data:
                found[param] = param.decode(data)
        return found

    def apply(self, amp, settle=0.02):
        """Load this patch by setting each named parameter individually.

        Rather than copying the file's raw bytes - whose effect blocks do
        not map one-to-one onto the amp's addresses - this walks the
        parameters the file defines and writes each one through the normal
        parameter path, which is known good for every section.

        Only parameters this project has mapped are set; anything else in
        the file is ignored. Returns (applied, skipped).
        """
        values = self.settings()

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
