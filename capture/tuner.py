"""Pitch detection: which note the guitar is playing, and how far off it is.

pitch() and note() are pure maths on numpy arrays. Tuner runs them on
the dry guitar from a Capture, on its own thread, and keeps the latest
reading for whoever asks. pitch() works in two steps:

1. YIN (de Cheveigné and Kawahara, 2002) finds the note: it repeats
   itself once every period, so slide the signal along a copy of itself
   and find the smallest shift at which the two line up again.
2. That reads a few cents sharp on a real string, whose upper harmonics
   are a little sharp themselves. So the fundamental alone is then
   measured exactly, in a narrow slice of the spectrum around step 1.

    frequency = pitch(samples)            # Hz, or None when there is no clear note
    name, octave, cents = note(frequency) # "E", 2, -3.4

    tuner = Tuner(capture)
    tuner.reading                         # ("E", 2, -3.4), or None
"""

import math
import queue
import threading

import numpy

from capture.stream import DRY, RATE

A4 = 440.0           # Hz: the reference every other note is counted from
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
LOWEST = 60.0        # Hz: just below a low string dropped to C (65.4)
HIGHEST = 1000.0     # Hz: above the high E's 12th fret (659)
SILENCE = -70.0      # dBFS: anything quieter is no note
THRESHOLD = 0.15     # how closely a shift must line up to count as the period
# Samples looked at together: 186 ms, fifteen periods of low E. Half
# that reads a low string up to 3 cents off when its fundamental is weak,
# because the much louder octave above leaks into it.
WINDOW = 8192
SEARCH = 50          # cents either side of YIN's answer to look for the fundamental
STEP = 10            # cents between the frequencies tried there
EVERY = 3072         # new samples between readings: 70 ms, about 14 a second


def level(samples):
    """How loud `samples` are, in dBFS: 0 is full scale."""
    return 10 * math.log10(numpy.mean(numpy.square(samples)) + 1e-20)


def pitch(samples, rate=RATE):
    """The frequency in Hz of the note in `samples`, or None if they are
    too quiet or have no clear repeating shape (a chord, a pick scrape).

    `samples` should be about WINDOW long; it must be longer than the
    period of LOWEST.
    """
    if level(samples) < SILENCE:
        return None
    samples = samples.astype(numpy.float64)
    rough = _period_pitch(samples, rate)
    if rough is None:
        return None
    return _fundamental(samples, rough, rate)


def _period_pitch(samples, rate):
    """Step 1, YIN: the frequency from the period, within a few cents."""
    shortest = int(rate / HIGHEST)    # the period of the highest note, in samples
    longest = int(rate / LOWEST)      # the period of the lowest note
    width = len(samples) - longest    # how many samples are compared at each shift

    # difference[shift] = sum of (samples[i] - samples[i + shift])^2 over
    # `width` samples: zero where the signal lines up with itself. Worked
    # out for every shift at once as a^2 + b^2 - 2ab: the squares from a
    # running total, the products from an FFT.
    first = samples[:width]
    size = 2 ** math.ceil(math.log2(len(samples) + width))
    spectrum = numpy.conj(numpy.fft.rfft(first, size)) * numpy.fft.rfft(samples, size)
    products = numpy.fft.irfft(spectrum, size)[:longest + 1]
    squares = numpy.concatenate(([0.0], numpy.cumsum(samples ** 2)))
    shifted = squares[width:width + longest + 1] - squares[:longest + 1]
    difference = squares[width] + shifted - 2 * products

    # Divided by the average difference up to that shift, so a good match
    # is near 0 and a bad one near 1 however loud the note is. Without
    # this, the tiny shifts always look best.
    normalised = numpy.ones(longest + 1)
    running = numpy.cumsum(difference[1:])
    normalised[1:] = difference[1:] * numpy.arange(1, longest + 1) / numpy.maximum(running, 1e-20)

    # The first shift that lines up well enough, then down to the bottom
    # of that dip. The first, not the best: two periods line up just as
    # well as one, and would read an octave low.
    good = numpy.flatnonzero(normalised[shortest:] < THRESHOLD)
    if len(good) == 0:
        return None
    shift = shortest + good[0]
    while shift < longest and normalised[shift + 1] < normalised[shift]:
        shift += 1

    # The true period falls between two whole samples. Fit a parabola
    # through the dip and its neighbours and take its lowest point - at
    # low E one sample is 3 cents, this gets well under one.
    if shortest < shift < longest:
        before, here, after = difference[shift - 1:shift + 2]
        curve = before - 2 * here + after
        if curve > 0:
            shift = shift + (before - after) / (2 * curve)
    return rate / shift


def _fundamental(samples, rough, rate):
    """Step 2: the exact frequency of the fundamental, near `rough`.

    Measures how strongly the samples contain each frequency from SEARCH
    cents below `rough` to SEARCH above (one bin of a Fourier transform
    each), and fits a parabola through the strongest and its neighbours.
    The second harmonic is a whole octave away, far outside the search,
    so the sharp upper harmonics no longer pull the answer up. The
    Blackman window fades the edges, so the cut-off ends of the block do
    not smear the loud octave above into the fundamental.

    In float32: twice as fast, and no less exact here. Multiplied and
    summed by hand rather than with `@`: that hands the work to OpenBLAS,
    whose threads then spin on all four cores - 200% CPU instead of 18.
    """
    weighted = ((samples - samples.mean()) * numpy.blackman(len(samples))).astype(numpy.float32)
    times = numpy.arange(len(samples)) / rate
    cents = numpy.arange(-SEARCH, SEARCH + 1, STEP)
    tried = rough * 2 ** (cents / 1200)
    phases = (2 * math.pi * numpy.outer(tried, times)).astype(numpy.float32)
    strength = numpy.abs((numpy.exp(-1j * phases) * weighted).sum(axis=1))

    best = int(numpy.argmax(strength))
    if best in (0, len(tried) - 1):
        return rough    # strongest at the edge: no clear peak, trust YIN
    # On a log scale the peak is very nearly a parabola.
    before, here, after = numpy.log(strength[best - 1:best + 2] + 1e-20)
    offset = (before - after) / (2 * (before - 2 * here + after))
    return rough * 2 ** ((cents[best] + offset * STEP) / 1200)


def note(frequency):
    """The nearest note to `frequency`: (name, octave, cents), where cents
    is how far off it is, -50 to +50, negative when flat."""
    number = 12 * math.log2(frequency / A4) + 69   # MIDI numbering: A4 is 69
    nearest = round(number)
    return NAMES[nearest % 12], nearest // 12 - 1, 100 * (number - nearest)


class Tuner:
    """Listens to the dry guitar on its own thread and keeps `reading`
    up to date: (name, octave, cents) of the note ringing, or None.

    A new note - or silence - only shows once two readings in a row
    agree on it. A single reading can catch the end of one note and the
    start of the next and come out as neither; this keeps it off screen.
    """

    def __init__(self, capture):
        self.reading = None
        self._capture = capture
        self._blocks = capture.listen()
        self._candidate = None     # the note the last reading found
        self._running = True
        self._thread = threading.Thread(target=self._run, name="tuner", daemon=True)
        self._thread.start()

    def close(self):
        self._running = False
        self._thread.join()
        self._capture.stop_listening(self._blocks)

    def _run(self):
        recent = numpy.zeros(WINDOW, numpy.float32)
        waiting = 0                # samples arrived since the last reading
        while self._running:
            try:
                block = self._blocks.get(timeout=0.5)
            except queue.Empty:
                continue           # the stream stalled; check _running again
            guitar = block[:, DRY]
            recent = numpy.concatenate((recent[len(guitar):], guitar))
            waiting += len(guitar)
            if waiting < EVERY:
                continue
            waiting = 0
            frequency = pitch(recent)
            self._settle(None if frequency is None else note(frequency))

    def _settle(self, found):
        found_note = found and found[:2]                # ("E", 2), or None
        shown_note = self.reading and self.reading[:2]
        if found_note == shown_note or found_note == self._candidate:
            self.reading = found
        self._candidate = found_note
