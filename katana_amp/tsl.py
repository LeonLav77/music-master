"""Read BOSS Tone Studio .tsl patch files.

    from tsl import load

    bank = load("my tones.tsl")
    for patch in bank:
        print(patch.name, patch.get("gain"))

    bank[0].apply()         # load the first patch into the amp


A .tsl file is JSON holding one or more patches, each a set of named byte
blocks ("UserPatch%Patch_0", "UserPatch%Fx(1)", ...). Those blocks are the
same bytes the amp keeps in memory, so a patch can be read here and sent
straight to the amp.

    from tsl import load

    bank = load("my tones.tsl")
    for patch in bank:
        print(patch.name, patch.get("gain"))

    bank[0].send()          # load the first patch into the amp
"""

import json
import time

from katana_amp.katana import LIVE_BASE, PARAMETERS, WIDE_PARAMETERS, KatanaError

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
        return "".join(chr(b) for b in raw if 0x20 <= b < 0x7F).strip()

    def memory(self):
        """Return {offset: byte} for everything this patch defines."""
        image = {}
        for block, start in BLOCK_OFFSETS.items():
            for index, byte in enumerate(self.blocks.get(block, [])):
                image[start + index] = byte
        return image

    def get(self, name):
        """Read a named parameter out of the patch, as the amp would report it."""
        image = self.memory()
        if name in WIDE_PARAMETERS:
            address = WIDE_PARAMETERS[name][0] - LIVE_BASE
            if address in image and address + 1 in image:
                return image[address] * 128 + image[address + 1]
            return None
        if name not in PARAMETERS:
            raise KatanaError(f"Unknown parameter {name!r}")
        return image.get(PARAMETERS[name][0] - LIVE_BASE)

    def settings(self):
        """Return {name: value} for every parameter the patch defines."""
        image = self.memory()
        found = {}
        for name, (address, _, _) in PARAMETERS.items():
            offset = address - LIVE_BASE
            if offset in image:
                found[name] = image[offset]
        for name, (address, _, _) in WIDE_PARAMETERS.items():
            offset = address - LIVE_BASE
            if offset in image and offset + 1 in image:
                found[name] = image[offset] * 128 + image[offset + 1]
        return found

    # Blocks that transfer reliably. The two 225-byte effect blocks are
    # deliberately excluded - see send().
    SAFE_BLOCKS = (
        "UserPatch%PatchName",
        "UserPatch%Patch_0",
    )

    # Switch addresses for the sections send() does not transfer.
    EFFECT_SWITCHES = (0x100, 0x300, 0x500, 0x520, 0x540, 0x550)

    def send(self, amp=None, settle=0.008, include_effects=False):
        """Raw byte copy of the patch. Prefer apply() - see below.

        This exists because it mirrors how the amp stores a patch, but it
        can only transfer the amp block faithfully. apply() sets each
        parameter by name instead and gets everything across.

        By default this sends only the patch name and the amp block -
        amp model, gain, the tone stack and the graphic EQ. Those verify
        byte-for-byte, and they are what defines the character of a tone.

        The effect blocks (Fx, Delay, Reverb, pedal) are NOT sent. Their
        bytes do not map one-to-one onto the amp's addresses: those
        regions contain two-byte values and reserved holes, and a flat
        copy puts roughly half the bytes in the wrong place - which
        switches on effects the patch never asked for. Working that
        layout out needs a capture of what Boss Tone Studio itself sends.
        Pass include_effects=True to send them anyway and see for
        yourself, but expect the effect sections to be wrong.

        Returns (bytes_written, mismatches).

        Does not touch the stored channels - use controls.save_to_patch()
        afterwards if you want to keep it.
        """
        if amp is None:
            from katana_amp.controls import connect

            amp = connect()

        blocks = dict(BLOCK_OFFSETS)
        if not include_effects:
            blocks = {k: v for k, v in blocks.items() if k in self.SAFE_BLOCKS}

        image = {}
        for block, start in blocks.items():
            for index, byte in enumerate(self.blocks.get(block, [])):
                image[start + index] = byte

        written = 0
        for offset, byte in sorted(image.items()):
            amp.write(amp._encode_address(LIVE_BASE + offset), [byte])
            written += 1
            if settle:
                time.sleep(settle)

        if not include_effects:
            # The effect blocks were not sent, so whatever the amp had
            # loaded is still running and has nothing to do with this
            # patch. Switch those sections off rather than leave a sound
            # the file never asked for.
            for offset in self.EFFECT_SWITCHES:
                amp.write(amp._encode_address(LIVE_BASE + offset), [0])
                time.sleep(settle)

        time.sleep(0.5)
        return written, self.verify(amp, image)

    def apply(self, amp=None, settle=0.02):
        """Load this patch by setting each named parameter individually.

        Where send() copies raw bytes - which only works for the amp
        block - this walks the parameters the file defines and writes
        each one through the normal parameter path. That path is known
        good for every section, so the effects, delays, reverb and gate
        come across too.

        Only parameters this project has mapped are set; anything else in
        the file is ignored. Returns (applied, skipped).
        """
        if amp is None:
            from katana_amp.controls import connect

            amp = connect()

        values = self.settings()

        # Effect switches last, so a section is configured before it is
        # switched on and you never hear a half-set effect.
        switches = {k: v for k, v in values.items() if k.endswith("_switch")}
        rest = {k: v for k, v in values.items() if not k.endswith("_switch")}

        applied = 0
        skipped = []
        for group in (rest, switches):
            for name, value in sorted(group.items()):
                try:
                    if name in WIDE_PARAMETERS:
                        amp.set_wide_parameter(name, value)
                    else:
                        amp.set_parameter(name, value)
                    applied += 1
                except KatanaError:
                    skipped.append(name)
                time.sleep(settle)

        return applied, skipped

    def verify(self, amp, image=None, chunk=0x10):
        """Compare the amp against `image`, reading in blocks for speed."""
        if image is None:
            image = self.memory()

        mismatches = []
        offsets = sorted(image)
        index = 0
        while index < len(offsets):
            start = offsets[index]
            run = [start]
            while (
                index + len(run) < len(offsets)
                and offsets[index + len(run)] == start + len(run)
                and len(run) < chunk
            ):
                run.append(start + len(run))
            try:
                got = amp.read(amp._encode_address(LIVE_BASE + start), len(run))
            except KatanaError:
                index += len(run)
                continue
            for position, offset in enumerate(run):
                if position < len(got) and got[position] != image[offset]:
                    mismatches.append(offset)
            index += len(run)
        return mismatches

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
    from katana import AMP_TYPES

    for index, patch in enumerate(load(path), 1):
        amp_type = patch.get("amp_type")
        print(
            f"{index}. {patch.name:20s} "
            f"{AMP_TYPES.get(amp_type, f'amp {amp_type}'):16s} "
            f"gain {patch.get('gain')}  vol {patch.get('volume')}"
        )
