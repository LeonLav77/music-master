"""Live monitoring: the amp's sound sent over the network as it happens,
so you can hear it in headphones plugged into a laptop.

Monitor sends the wet amp sound (channel 1, effects and all - channel 2
is the same) from a Capture in UDP packets, one per block. UDP never
waits for a lost packet to be sent again, so a packet lost on the way is
a 5.8 ms gap rather than everything behind it stalling, as it would
over TCP.

Nobody is set up in advance. A listener asks for the sound by sending
any packet to PORT, and keeps asking about once a second; one that has
not asked for EXPIRE seconds is dropped. Since the sound is the answer
to packets the laptop sent first, the laptop's firewall lets it in.

Each packet is:

    4 bytes      its number, counting up from 0: unsigned, little-endian
    the rest     BLOCK samples: 16-bit signed, little-endian, mono, 44.1 kHz

The numbers let a listener tell a lost packet (a gap) from a late one
(smaller than the one before). 16 bits rather than float32 so a packet
fits in one WiFi frame (1500 bytes) even at 512 frames a block: a bigger
one is split in two, and losing either half loses all of it.

    monitor = Monitor(capture)
    monitor.listeners       # [(address, port), ...] being sent to
    monitor.close()
"""

import queue
import socket
import struct
import threading
import time

import numpy

from capture.stream import WET

PORT = 5005          # UDP port listeners ask on
EXPIRE = 5.0         # seconds a listener stays without asking again
HEADER = struct.Struct("<I")
FULL_SCALE = 32767   # the largest 16-bit sample


def to_16_bit(sound):
    """float32 samples, -1 to 1, as little-endian 16-bit bytes."""
    whole = numpy.round(sound * FULL_SCALE)
    return numpy.clip(whole, -FULL_SCALE, FULL_SCALE).astype("<i2").tobytes()


class Monitor:
    def __init__(self, capture, port=PORT):
        # The socket first: if the port is taken, this raises OSError
        # before anything is listening to the capture.
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(("0.0.0.0", port))
        self._socket.setblocking(False)

        self._heard = {}           # listener address -> when it last asked
        self._number = 0           # of the next packet
        self._capture = capture
        self._blocks = capture.listen()
        self._running = True
        self._thread = threading.Thread(target=self._run, name="monitor", daemon=True)
        self._thread.start()

    @property
    def listeners(self):
        return list(self._heard)

    def close(self):
        self._running = False
        self._thread.join()
        self._capture.stop_listening(self._blocks)
        self._socket.close()

    # --- the monitor thread ------------------------------------------------

    def _run(self):
        while self._running:
            self._read_requests()
            try:
                block = self._blocks.get(timeout=0.5)
            except queue.Empty:
                continue           # the stream stalled; check _running again
            if not self._heard:
                continue           # nobody listening: the block goes nowhere
            packet = HEADER.pack(self._number) + to_16_bit(block[:, WET])
            self._number = (self._number + 1) % 2 ** 32
            for address in self._heard:
                try:
                    self._socket.sendto(packet, address)
                except OSError:
                    pass           # e.g. WiFi dropped; it stops asking and expires

    def _read_requests(self):
        """Note every listener that asked since the last block, and drop
        the ones that stopped asking."""
        now = time.monotonic()
        heard = dict(self._heard)
        while True:
            try:
                _request, address = self._socket.recvfrom(64)
            except OSError:        # BlockingIOError: nothing more waiting
                break
            heard[address] = now
        # A new dict rather than changing the old one, so `listeners`,
        # read from another thread, never sees one half-changed.
        self._heard = {address: asked for address, asked in heard.items()
                       if now - asked < EXPIRE}
