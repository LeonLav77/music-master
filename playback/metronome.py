"""The metronome: clicks placed by counting samples, never by sleeping.

Other threads only set `bpm`, `beats_per_bar` and `volume`, which the
audio thread reads once per beat - so a tempo change takes effect from the
next beat. start() and stop() are for the audio thread only; everyone else
goes through Player, which queues them.
"""

from playback.sounds import RATE, beep


class Metronome:
    def __init__(self, bpm=120, beats_per_bar=4, volume=1.0):
        self.bpm = bpm
        self.beats_per_bar = beats_per_bar
        self.volume = volume

        self._accent = beep(accent=True)
        self._normal = beep(accent=False)
        self._next_beat = None   # frame of the next click; None when stopped
        self._beat = 0
        self._beats_left = None  # stop by itself after this many; None = never
        self._sounding = []      # (start frame, sound) of clicks still ringing

    def frames_per_beat(self):
        return RATE * 60 / self.bpm

    def is_running(self):
        return self._next_beat is not None

    def start(self, position, beats=None):
        """Beat 1 at frame `position`. With `beats`, stop after that many -
        a count-in."""
        self._next_beat = position
        self._beat = 0
        self._beats_left = beats

    def stop(self):
        self._next_beat = None

    def render(self, out, position):
        """Add the clicks that fall inside `out`, a block starting at frame
        `position`."""
        end = position + len(out)
        while self._next_beat is not None and self._next_beat < end:
            accent = self._beat % self.beats_per_bar == 0
            sound = self._accent if accent else self._normal
            self._sounding.append((round(self._next_beat), sound))
            self._beat += 1
            if self._beats_left is not None and self._beat >= self._beats_left:
                self.stop()
                break
            # A float, so a tempo whose beat is not a whole number of frames
            # does not drift.
            self._next_beat += self.frames_per_beat()

        # A click is longer than some blocks, so one can start in this block
        # and finish in the next: `offset` is negative for those.
        still_sounding = []
        for start, sound in self._sounding:
            offset = start - position
            first = max(offset, 0)
            last = min(offset + len(sound), len(out))
            out[first:last] += sound[first - offset:last - offset] * self.volume
            if offset + len(sound) > len(out):
                still_sounding.append((start, sound))
        self._sounding = still_sounding
