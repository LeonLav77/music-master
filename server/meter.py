"""The input meter: how loud the guitar is, measured from the amp's USB audio.

The Katana is also a USB sound card, and it sends the processed guitar
sound - what the speaker plays - to the Pi. This listens to it with
`arecord` (the same tool you would test it with by hand), measures each
50 ms of audio, and sends the result to every browser:

    {"type": "level", "peak": 0.31, "rms": 0.08}

Both are 0 (silence) to 1 (the loudest the amp can send). `peak` is the
single loudest sample, `rms` the average loudness - what a meter bar shows.

Only one program can record from the amp at a time, so while the server
runs, a hand-run `arecord` will say the device is busy.
"""

import array
import asyncio
import contextlib
import math
import subprocess
import threading

from server import amp

# Mono is enough for a meter; plughw lets ALSA convert from the amp's own
# format to this one.
RECORD = ["arecord", "-q", "-D", "plughw:KATANA", "-f", "S16_LE",
          "-r", "44100", "-c", "1", "-t", "raw"]
SAMPLE_RATE = 44100
CHUNK_SECONDS = 0.05                                     # 20 measurements a second
CHUNK_BYTES = int(SAMPLE_RATE * CHUNK_SECONDS) * 2       # 2 bytes per 16-bit sample
FULL_SCALE = 32768
RETRY_SECONDS = 2.0                                      # when the amp is not there

_stop = threading.Event()
_recorder = None


def measure(chunk):
    """(peak, rms) of a chunk of 16-bit audio, each 0..1."""
    samples = array.array("h", chunk)
    peak = max(abs(sample) for sample in samples) / FULL_SCALE
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / FULL_SCALE
    return peak, rms


def _listen(loop):
    """Runs in its own thread: record, measure, send - and start again if
    the amp goes away."""
    global _recorder
    while not _stop.is_set():
        try:
            _recorder = subprocess.Popen(RECORD, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            return                                       # no arecord here (not a Pi)
        while not _stop.is_set():
            chunk = _recorder.stdout.read(CHUNK_BYTES)
            if len(chunk) < CHUNK_BYTES:
                break                                    # the amp went away
            peak, rms = measure(chunk)
            message = {"type": "level", "peak": round(peak, 3), "rms": round(rms, 3)}
            asyncio.run_coroutine_threadsafe(amp.broadcast(message), loop)

        _recorder.kill()
        _recorder.wait()
        # Drop the meter to zero rather than leave it frozen at the last value.
        asyncio.run_coroutine_threadsafe(
            amp.broadcast({"type": "level", "peak": 0, "rms": 0}), loop)
        _stop.wait(RETRY_SECONDS)


@contextlib.asynccontextmanager
async def lifespan(app):
    """Listen for as long as the server is up."""
    listener = threading.Thread(target=_listen, args=(asyncio.get_running_loop(),),
                                daemon=True)
    listener.start()
    try:
        yield
    finally:
        _stop.set()
        if _recorder is not None and _recorder.poll() is None:
            _recorder.kill()                             # unblocks the read
        listener.join(timeout=2)
