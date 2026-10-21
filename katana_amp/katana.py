"""Control a BOSS Katana MkII amplifier over USB MIDI SysEx.

Reusable module: no printing, no CLI, no interactive prompts, so it can later
be driven headless from a Raspberry Pi UI.

Protocol notes (verified against a Katana MkII 100W head):

  Every message is  F0 41 00 00 00 00 33 <op> <addr:4> <payload> <cksum> F7
  where op 0x11 = query and op 0x12 = set.

  On a query, the payload is a 4-byte length; the amp answers with a 0x12
  message carrying the data. On a set, the payload is the data itself.

  The MkII does NOT respond to the 0x00 00 04 xx "front panel" addresses
  documented for the first-generation Katana. Live amp parameters are at
  0x60 00 00 xx instead, laid out in the same field order. The stored
  patches 1-9 mirror that layout from 0x10 00 00 xx up.

Every setting the amp exposes is a member of the `Param` enum, in
param.py; the Katana class here reads and writes them.
"""

import time

import mido

# --- Wire format -----------------------------------------------------------

MANUFACTURER_ID = 0x41  # Roland
MODEL_ID = (0x00, 0x00, 0x00, 0x33)
DEVICE_ID = 0x00

OP_QUERY = 0x11
OP_SET = 0x12

# Live ("temporary patch") area. Everything the amp is playing right now
# lives here; user patches 1-9 mirror the same layout at 0x10000000 up.
#
# Addresses below are the MkII map, cross-checked against the community
# address map on VGuitarForums and verified by read/write on a MkII 100W
# head. They are NOT the same as the 00 00 04 xx addresses documented for
# the first-generation Katana, which this amp ignores entirely.
LIVE_BASE = 0x60000000

# Stored patch names are 16 ASCII bytes.
NAME_LENGTH = 16

class KatanaError(Exception):
    """Raised when the amp cannot be reached or does not answer."""


def checksum(payload):
    """Roland 7-bit checksum over the address + data bytes."""
    total = 0
    for byte in payload:
        total = (total + byte) & 0x7F
    return (0x80 - total) & 0x7F


def _encode_length(length):
    """Encode a byte count as Roland's 4-byte 7-bit value."""
    return [
        (length // 0x200000) % 0x80,
        (length // 0x4000) % 0x80,
        (length // 0x80) % 0x80,
        length % 0x80,
    ]


def find_ports():
    """Return the MIDI port names that look like a Katana's control port.

    The amp exposes two ports and only MIDI 1 answers SysEx, so both tokens
    have to match. Relying on MIDI 1 sorting first works on a desktop and is
    a coin flip on a Pi, where ALSA enumeration order is not guaranteed.

    Ports that only match KATANA are returned after the MIDI 1 ones rather
    than dropped: on a host that names them differently, a port that cannot
    answer beats no port at all.
    """
    katana = [name for name in mido.get_output_names() if "KATANA" in name.upper()]
    control = [name for name in katana if "MIDI 1" in name.upper()]
    return control + [name for name in katana if name not in control]


# Program Change numbers for channel selection, from the official manual's
# "RECOGNIZED RECEIVE DATA" table. These are what actually switch channels -
# writing the led_* addresses does not.
CHANNELS = {
    "a1": 1, "a2": 2, "a3": 3, "a4": 4, "panel": 5,
    "b1": 6, "b2": 7, "b3": 8, "b4": 9,
}

# The channel the amp is on, as a two-byte program number counted from 0:
# B2 (program 7) reads [0, 6]. Verified on a MkII by switching channels on
# the panel and reading it back. The amp sends nothing when its CH buttons
# are pressed, so reading this is the only way to know.
CURRENT_CHANNEL = 0x00010000

def decode_name(raw):
    """A patch name from its bytes: printable ASCII, padding stripped."""
    return "".join(chr(byte) for byte in raw if 0x20 <= byte < 0x7F).strip()


class Katana:
    """A connection to one Katana amplifier.

    Usable as a context manager so the MIDI ports always get closed:

        with Katana() as amp:
            print(amp.get_parameter(Param.GAIN))    # Param from param.py
    """

    def __init__(self, port_name=None, timeout=1.0, midi_channel=1):
        if port_name is None:
            found = find_ports()
            if not found:
                raise KatanaError(
                    "No Katana MIDI port found. Is the amp powered on and "
                    "connected over USB?"
                )
            # find_ports puts the SysEx control port (MIDI 1) first.
            port_name = found[0]

        self.port_name = port_name
        self.timeout = timeout
        # The amp's MIDI receive channel, 0-based. Factory default is CH 1;
        # it is chosen by holding a CH button while powering on.
        self.midi_channel = midi_channel - 1
        try:
            self._out = mido.open_output(port_name)
            self._in = mido.open_input(port_name)
        except (IOError, OSError) as exc:
            raise KatanaError(f"Could not open MIDI port {port_name!r}: {exc}")

    # --- lifecycle ---------------------------------------------------------

    def close(self):
        for port in (self._out, self._in):
            if port is not None and not port.closed:
                port.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False

    # --- raw SysEx ---------------------------------------------------------

    def _send(self, op, address, payload):
        body = list(address) + list(payload)
        # Header is fixed: 41 00 00 00 00 33 <op>
        data = [MANUFACTURER_ID, DEVICE_ID, *MODEL_ID, op]
        self._out.send(mido.Message("sysex", data=data + body + [checksum(body)]))

    def read(self, address, length, attempts=3):
        """Query `length` bytes at `address`; return them as a list of ints.

        The amp occasionally drops a reply when it is busy - especially
        while a burst of writes is still settling - so a timed-out read is
        retried rather than reported as a missing address.
        """
        for attempt in range(attempts):
            # Drop anything the amp sent unprompted so we read our own reply.
            for _ in self._in.iter_pending():
                pass

            self._send(OP_QUERY, address, _encode_length(length))

            deadline = time.time() + self.timeout
            received = {}
            while time.time() < deadline:
                message = self._in.poll()
                if message is None:
                    time.sleep(0.005)
                    continue
                if message.type != "sysex":
                    continue
                # mido strips the leading F0, so: 41 00 00 00 00 33 12 <addr:4> ...
                data = list(message.data)
                offset = data[7:11]
                chunk = data[11:-1]
                # Key each chunk by its position relative to what we asked for,
                # so multi-chunk replies reassemble in the right order.
                start = Katana._decode_address(offset) - Katana._decode_address(address)
                received[start] = chunk
                if sum(len(piece) for piece in received.values()) >= length:
                    break

            if received:
                result = []
                for start in sorted(received):
                    result.extend(received[start])
                return result[:length]

            if attempt + 1 < attempts:
                time.sleep(0.05 * (attempt + 1))

        raise KatanaError(
            f"No reply from the amp for address "
            f"{' '.join(f'{byte:02X}' for byte in address)} after {attempts} attempts."
        )

    def write(self, address, data):
        """Set the bytes at `address`. Fire-and-forget; the amp does not ack."""
        self._send(OP_SET, address, list(data))

    # --- parameters --------------------------------------------------------

    @staticmethod
    def _decode_address(address):
        """Collapse a 4-byte 7-bit address into a single integer."""
        first, second, third, fourth = address
        return (first << 21) | (second << 14) | (third << 7) | fourth

    @staticmethod
    def _encode_address(value):
        """Split an absolute address into its four 7-bit SysEx bytes."""
        return (
            (value >> 24) & 0x7F,
            (value >> 16) & 0x7F,
            (value >> 8) & 0x7F,
            value & 0x7F,
        )

    def get_parameter(self, param):
        """Read one setting (a Param), in real units."""
        return param.decode(self.read(self._encode_address(param.address()), param.size()))

    def set_parameter(self, param, value):
        """Write one setting (a Param) in real units, refusing values the
        amp would clamp."""
        if not isinstance(value, int):
            raise KatanaError(f"{param} must be an integer, got {value!r}")
        low, high = param.range()
        if not low <= value <= high:
            raise KatanaError(f"{param} must be between {low} and {high}, got {value}")
        self.write(self._encode_address(param.address()), param.encode(value))

    def select_channel(self, channel):
        """Switch tone-setting channel with a Program Change.

        `channel` is a name from CHANNELS ("a1".."a4", "panel", "b1".."b4")
        or a raw program number 1-9. This is the documented way to change
        channels; the led_* parameters only report the result.
        """
        if isinstance(channel, str):
            key = channel.lower().replace(" ", "").replace("ch", "")
            if key not in CHANNELS:
                known = ", ".join(CHANNELS)
                raise KatanaError(f"Unknown channel {channel!r}. Known: {known}")
            program = CHANNELS[key]
        else:
            program = channel
        if not 1 <= program <= 9:
            raise KatanaError(f"Channel program must be 1-9, got {program}")
        self._out.send(
            mido.Message("program_change", channel=self.midi_channel, program=program - 1)
        )
        return program

    def read_channel(self):
        """The channel the amp is on: "a1".."a4", "panel" or "b1".."b4".

        None if the amp reports a program that is not one of CHANNELS.
        """
        high, low = self.read(self._encode_address(CURRENT_CHANNEL), 2, attempts=1)
        program = high * 128 + low + 1
        return next((name for name, pc in CHANNELS.items() if pc == program), None)

    def send_control_change(self, control, value):
        """Send a raw Control Change on the amp's receive channel."""
        if not 0 <= value <= 127:
            raise KatanaError(f"CC value must be 0-127, got {value}")
        self._out.send(
            mido.Message(
                "control_change", channel=self.midi_channel,
                control=control, value=value,
            )
        )

    # --- Patch memory ------------------------------------------------------
    #
    # User patches 1-9 mirror the live area's layout, starting at
    # 0x10000000 and 0x10000 apart. Writing there edits the stored sound
    # without disturbing what is playing.

    PATCH_BASE = 0x10000000
    PATCH_STRIDE = 0x10000

    @staticmethod
    def patch_address(patch, offset=0):
        """Absolute address of `offset` within stored patch 1-9."""
        if not 1 <= patch <= 9:
            raise KatanaError(f"Patch must be 1-9, got {patch}")
        return Katana.PATCH_BASE + (patch - 1) * Katana.PATCH_STRIDE + offset

    def read_patch(self, patch, offset=0, length=1):
        """Read bytes from a stored patch."""
        return self.read(self._encode_address(self.patch_address(patch, offset)), length)

    def write_patch(self, patch, offset, data):
        """Write bytes into a stored patch."""
        self.write(self._encode_address(self.patch_address(patch, offset)), data)

    # The regions a patch actually occupies, as (start, length) offsets from
    # the base of the patch. The amp leaves gaps between them and does not
    # answer reads there, so a full copy has to skip those.
    PATCH_REGIONS = ((0x000, 0x740), (0x780, 0x040), (0x800, 0x100))

    def copy_live_to_patch(self, patch):
        """Copy the entire live sound into stored patch 1-9.

        Copies every region the patch occupies - amp, effects, EQ, delays,
        reverb and the rest - not just the amp block. Returns the number of
        bytes written.
        """
        chunk = 0x20
        written = 0
        for start, length in self.PATCH_REGIONS:
            for offset in range(start, start + length, chunk):
                size = min(chunk, start + length - offset)
                block = self.read(self._encode_address(LIVE_BASE + offset), size)
                self.write_patch(patch, offset, block)
                written += len(block)
        return written
