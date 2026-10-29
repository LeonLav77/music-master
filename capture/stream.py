"""The Katana's USB input: one audio stream from the amp, shared by
whoever listens.

The Katana sends 4 channels at 44.1 kHz: 1-2 are the amp's sound with
its effects, 3-4 the dry guitar from before the preamp (the same signal
twice). The card hands us BLOCK frames at a time on its own thread, and
_receive() only copies each block into every listener's queue - anything
slow in there and the card drops audio.

    with Capture() as capture:
        blocks = capture.listen()
        block = blocks.get()        # BLOCK x 4 float32, between -1 and 1
        guitar = block[:, DRY]
"""

import queue

import sounddevice

RATE = 44100         # the only rate the Katana offers
CHANNELS = 4
BLOCK = 512          # frames per callback: 11.6 ms at 44.1 kHz
WET = 0              # column of the amp's sound, effects and all
DRY = 2              # column of the guitar before the preamp
KATANA_NAME = "KATANA"


class CaptureError(Exception):
    """Raised when the Katana's input cannot be found or opened."""


def find_input(name=KATANA_NAME):
    """The index of the first 4-channel input whose name contains `name`.

    Opened directly through ALSA, like the player's output: PipeWire
    hands back channels 3-4 as silence.
    """
    for index, device in enumerate(sounddevice.query_devices()):
        if name.lower() in device["name"].lower() and device["max_input_channels"] >= CHANNELS:
            return index
    raise CaptureError(f"No audio input named like {name!r} - is the amp on and plugged in?")


class Capture:
    def __init__(self, device=None):
        self.overruns = 0     # blocks the card dropped because we were late
        self._listeners = []

        try:
            self._stream = sounddevice.InputStream(
                samplerate=RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=BLOCK,
                latency="high",
                device=find_input() if device is None else device,
                callback=self._receive,
            )
            self._stream.start()
        except sounddevice.PortAudioError as exc:
            raise CaptureError(f"Could not open the amp's input: {exc}")

    # --- lifecycle ---------------------------------------------------------

    def close(self):
        self._stream.stop()
        self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
        return False

    def latency(self):
        """Seconds from the sound reaching the card to the block holding it
        being handed over: the card's buffer."""
        return self._stream.latency

    # --- listeners: safe from any thread -----------------------------------

    def listen(self):
        """A new queue that gets every block from now on. Read it promptly:
        it keeps growing until it is read."""
        blocks = queue.SimpleQueue()
        # A new list rather than append(), so the audio thread never sees
        # one half-changed.
        self._listeners = self._listeners + [blocks]
        return blocks

    def stop_listening(self, blocks):
        self._listeners = [listener for listener in self._listeners if listener is not blocks]

    # --- the audio thread --------------------------------------------------

    def _receive(self, data, frames, timing, status):
        if status.input_overflow:
            self.overruns += 1
        # The card reuses `data` for the next block, so each listener
        # gets a copy.
        for listener in self._listeners:
            listener.put(data.copy())
