"""The click sounds, built with numpy when the program starts."""

import numpy

RATE = 48000


def beep(accent=False):
    """A short, softly squared beep, chosen by ear through the amp.

    Beat 1 is higher and peaks at full scale; the others are 3 dB lower.
    The headroom for the amp is in the Pi's PCM mixer (-3 dB), not here:
    at 0 dB a full-scale beep crunches.
    """
    moments = numpy.arange(int(0.12 * RATE)) / RATE
    freq = 1500 if accent else 1000
    # tanh flattens the tops of the sine, so it sits near its peak for
    # longer and sounds louder than a pure sine with the same peak.
    tone = numpy.tanh(4 * numpy.sin(2 * numpy.pi * freq * moments))
    hold = 0.04
    fade = numpy.where(moments < hold, 1.0, numpy.exp(-(moments - hold) / 0.04))
    shape = tone * fade
    peak = 1.0 if accent else 0.7
    # One column, so it adds onto both channels of a (frames, 2) block.
    return (shape / abs(shape).max() * peak).astype(numpy.float32)[:, numpy.newaxis]
