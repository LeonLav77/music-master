"""Recording what you hear: the amp's sound (channels 1-2) and what the Pi
sends to its AUX - the song, the clicks - in one 24-bit WAV file.

The amp does not pass AUX on over USB, so that part is added here. While
recording, this thread writes two files - the audio threads never wait
on the SD card:

- take.wav       the amp, exactly as it sent it (24 bits fit float32)
- take.wav.aux   what the Pi sent to the jack: 48 kHz, 16-bit, raw

stop() then has ffmpeg turn the AUX part into 44.1 kHz, shift it to where
you heard it while playing, and mix it into take.wav. If nothing but
silence was sent, the take is left as it is.

The two clocks count the same second to within 12.6 ppm (measured): 3 ms
over a 4-minute song, too little to hear, so the shift is worked out once.

    recorder = Recorder(capture, player)
    recorder.start(Path("recordings/take.wav"))
    recorder.elapsed()      # seconds recorded so far
    recorder.peak           # loudest amp sample so far: 1.0 means it clipped
    recorder.stop()         # finishes the files and mixes them: seconds
"""

import os
import queue
import subprocess
import threading
import wave

import numpy

from capture.stream import RATE, WET
from playback.sounds import RATE as AUX_RATE

FULL_SCALE = 2 ** 23     # a 24-bit sample runs from -2^23 to 2^23 - 1
# How loud the AUX part goes into the take, in dB. The amp's AUX knob sets
# the balance you hear; this is set by ear to match it.
AUX_LEVEL = -14.0
# What the amp itself adds to the delay, on top of the two buffers
# PortAudio reports. Set by ear: positive if you sound early on a take.
EXTRA_DELAY = 0.0        # seconds


class RecorderError(Exception):
    """Raised when a recording cannot be started or written."""


def to_24_bit(sound):
    """float32 frames, -1 to 1, as little-endian 24-bit WAV bytes."""
    whole = numpy.clip(numpy.round(sound * FULL_SCALE), -FULL_SCALE, FULL_SCALE - 1).astype("<i4")
    # Each sample is 4 bytes, lowest first: keep the lower 3 of every 4.
    return whole.view(numpy.uint8).reshape(-1, 4)[:, :3].tobytes()


class Recorder:
    def __init__(self, capture, player=None):
        self.path = None       # the file being recorded, or the last one
        self.frames = 0        # amp frames written to it
        self.peak = 0.0        # the loudest amp sample in it, 0 to 1
        self.error = None      # why writing stopped, if it did
        self._capture = capture
        self._player = player  # None: no AUX part, just the amp
        self._thread = None

    def is_recording(self):
        return self._thread is not None

    def elapsed(self):
        return self.frames / RATE

    def start(self, path):
        if self.is_recording():
            raise RecorderError("Already recording")
        try:
            self._file = wave.open(str(path), "wb")
        except OSError as exc:
            raise RecorderError(f"Could not create {path}: {exc}")
        try:
            self._aux_file = open(f"{path}.aux", "wb")
        except OSError as exc:
            self._file.close()
            raise RecorderError(f"Could not create {path}.aux: {exc}")
        self._file.setnchannels(2)
        self._file.setsampwidth(3)
        self._file.setframerate(RATE)
        self.path, self.frames, self.peak, self.error = path, 0, 0.0, None
        self._aux_start = None     # player position of the first AUX block
        self._aux_loud = False     # anything but silence sent?
        self._gap_total = 0.0      # see _shift()
        self._gap_count = 0
        self._blocks = self._capture.listen()
        self._sent = self._player.listen() if self._player else queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run, name="recorder", daemon=True)
        self._thread.start()

    def stop(self):
        """Stop, finish the take and mix the AUX part in - a few seconds
        for a long take, so call it from a thread. Returns the path, or
        None if nothing was recording."""
        if not self.is_recording():
            return None
        # No new blocks from here on. The None goes in behind the ones
        # still queued: the thread writes those, reaches it and finishes.
        self._capture.stop_listening(self._blocks)
        if self._player:
            self._player.stop_listening(self._sent)
        self._blocks.put(None)
        self._thread.join()
        self._thread = None

        aux = f"{self.path}.aux"
        if self._aux_loud and self.frames and self.error is None:
            try:
                self._mix(aux)
            except subprocess.CalledProcessError as exc:
                self.error = f"Mixing in the AUX part failed: {exc.stderr.decode().strip()}"
        os.remove(aux)
        return self.path

    # --- the recorder thread -----------------------------------------------

    def _run(self):
        try:
            while True:
                block = self._blocks.get()
                if block is None:
                    break
                # Read now, as close as we can to the block arriving.
                sent = self._player.position if self._player else 0

                sound = block[:, WET:WET + 2]
                self.peak = max(self.peak, float(numpy.abs(sound).max()))
                # writeframes also updates the length in the header, so
                # the file plays even if the server dies mid-take.
                self._file.writeframes(to_24_bit(sound))
                self.frames += len(sound)

                # The player counts 48,000 frames a second and the take
                # 44,100, so frames cannot be compared - seconds can.
                self._gap_total += sent / AUX_RATE - self.frames / RATE
                self._gap_count += 1
                self._write_aux()
            self._write_aux()
        except OSError as exc:   # the SD card is full, say
            self.error = str(exc)
            self._capture.stop_listening(self._blocks)
        finally:
            self._file.close()
            self._aux_file.close()

    def _write_aux(self):
        while not self._sent.empty():
            position, frames = self._sent.get_nowait()
            if self._aux_start is None:
                self._aux_start = position
            self._aux_loud = self._aux_loud or bool(frames.any())
            self._aux_file.write((frames * 32767).astype("<i2").tobytes())

    # --- mixing --------------------------------------------------------------

    def _shift(self):
        """Seconds into the take at which the AUX file's first frame belongs.

        Every amp block that arrived noted how far the player had got:
        `gap` is the player's clock minus the take's, averaged over all
        of them. A frame the player sent at time p reached your ears a
        jack's buffer later, and what you played then reached us an amp
        buffer later still - so it belongs at p - gap + both buffers.
        """
        gap = self._gap_total / self._gap_count
        delay = self._player.latency() + self._capture.latency() + EXTRA_DELAY
        return self._aux_start / AUX_RATE - gap + delay

    def _mix(self, aux):
        # Too early to shift back cannot happen in practice - the delay is
        # over 100 ms - so it is simply held at the start.
        frames = max(round(self._shift() * RATE), 0)
        mixed = f"{self.path}.mixed.wav"
        # The .aux file is bare numbers, so ffmpeg is told what they are:
        # 48 kHz, 16-bit, stereo. aresample turns them into 44.1 kHz like
        # the take; only then can amix add the two frame by frame.
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(self.path),
             "-f", "s16le", "-ar", str(AUX_RATE), "-ac", "2", "-i", aux,
             "-filter_complex",
             f"[1]aresample={RATE},adelay=delays={frames}S:all=1,volume={AUX_LEVEL}dB[aux];"
             "[0][aux]amix=inputs=2:duration=first:normalize=0",
             "-c:a", "pcm_s24le", mixed],
            check=True, capture_output=True,
        )
        os.replace(mixed, self.path)
