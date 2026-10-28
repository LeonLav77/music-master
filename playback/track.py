"""A backing track: decoded once into memory, then copied out block by block.

ffmpeg does the decoding - any format it reads, resampled to RATE - so
nothing here knows about MP3 or FLAC. The samples stay as int16, half the
size of float32, and are scaled into floats one block at a time.

Like the metronome, start(), pause() and seek() are for the audio thread
only; other threads go through Player. `volume` is a plain setting.
"""

import subprocess

import numpy

from playback.sounds import RATE

# Through the Pi's jack a song is quiet even at full scale, so quiet songs
# are boosted into a limiter, which holds the peaks down instead of clipping.
# The boost is TARGET_LOUDNESS minus the song's own level: Seek & Destroy is
# -17 dB and sounded right +10 dB louder, so the target is -7. The limiter
# takes some of it back (that song ends up near -12); an already-loud modern
# master gets little or no boost.
TARGET_LOUDNESS = -7.0   # dB, average (RMS)
MAX_BOOST = 12.0         # dB
PCM = ["-f", "s16le", "-ac", "2", "-ar", str(RATE)]


class TrackError(Exception):
    """Raised when a file cannot be decoded."""


def _ffmpeg(arguments, name, data=None):
    result = subprocess.run(["ffmpeg", "-v", "error", *arguments], input=data, capture_output=True)
    if result.returncode != 0:
        raise TrackError(f"Could not decode {name}: {result.stderr.decode().strip()}")
    return result.stdout


def loudness(samples):
    """Average level of int16 samples in dB (RMS), a chunk at a time so a
    long song never needs a float copy of all of it."""
    total = 0.0
    for start in range(0, len(samples), RATE * 10):
        chunk = samples[start:start + RATE * 10].astype(numpy.float32) / 32768
        total += float(numpy.square(chunk).sum())
    return 10 * numpy.log10(total / max(samples.size, 1) + 1e-12)


def decode(path):
    """The samples of an audio file as an int16 array of shape (frames, 2),
    made louder if the song is quiet."""
    raw = _ffmpeg(["-i", str(path), *PCM, "-"], path)
    boost = min(TARGET_LOUDNESS - loudness(numpy.frombuffer(raw, dtype=numpy.int16)), MAX_BOOST)
    if boost >= 0.5:
        limiter = f"volume={boost:.1f}dB,alimiter=limit=0.89:level=false"
        raw = _ffmpeg([*PCM, "-i", "-", "-af", limiter, *PCM, "-"], path, data=raw)
    return numpy.frombuffer(raw, dtype=numpy.int16).reshape(-1, 2)


class Track:
    def __init__(self, name, samples, volume=1.0):
        self.name = name
        self.samples = samples
        self.volume = volume

        self._starts_at = None   # stream frame it plays from; None when not playing
        self._position = 0       # next frame of the track to play

    @classmethod
    def load(cls, path):
        return cls(str(path), decode(path))

    def duration(self):
        return len(self.samples) / RATE

    def elapsed(self):
        return self._position / RATE

    def is_playing(self):
        return self._starts_at is not None

    def start(self, at):
        """Play from the current place in the track, beginning at stream
        frame `at` - which can be in the future, for a count-in."""
        self._starts_at = at

    def pause(self):
        self._starts_at = None

    def seek(self, frame):
        self._position = min(max(frame, 0), len(self.samples))

    def render(self, out, position):
        """Add this block's slice of the track to `out`, a block starting at
        frame `position`."""
        if self._starts_at is None:
            return
        # Zero once the start has passed; part-way into the block in the
        # block where a count-in ends; past the end while still counting in.
        first = max(self._starts_at - position, 0)
        if first >= len(out):
            return

        count = min(len(out) - first, len(self.samples) - self._position)
        chunk = self.samples[self._position:self._position + count]
        out[first:first + count] += chunk * (self.volume / 32768)
        self._position += count

        if self._position >= len(self.samples):
            self._starts_at = None
            self._position = 0
