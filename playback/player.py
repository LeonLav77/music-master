"""The player: one audio stream to the Pi's headphone jack, filled by us.

The sound card asks for the next BLOCK frames whenever it needs them, on
its own thread; _fill() mixes everything into that block. Nothing here
sleeps or reads a clock - the card plays exactly RATE frames a second, so
counting frames is the timing.

Settings (metronome.bpm, track.volume, ...) are plain attributes. Actions
(play, pause, seek, ...) are queued and run by the audio thread at the start
of its next block, because only it knows which frame "now" is - and that is
what lets a count-in and a track start exactly one beat apart.

    with Player() as player:
        player.metronome.bpm = 100
        player.play(library.get("blues.mp3"), count_in=4)
"""

import queue

import numpy
import sounddevice

from playback.metronome import Metronome
from playback.sounds import RATE

BLOCK = 512          # frames per callback: 10.7 ms at 48 kHz
JACK_NAME = "Headphones"


class PlaybackError(Exception):
    """Raised when the audio output cannot be found or opened."""


def find_output(name=JACK_NAME):
    """The index of the first stereo output whose name contains `name`.

    Opened directly through ALSA rather than through PipeWire: one layer
    less, and it works with nobody logged in.
    """
    for index, device in enumerate(sounddevice.query_devices()):
        if name.lower() in device["name"].lower() and device["max_output_channels"] >= 2:
            return index
    raise PlaybackError(f"No audio output named like {name!r}")


class Player:
    def __init__(self, device=None):
        self.metronome = Metronome()
        self.track = None     # the track playing or paused; set by the audio thread
        self.position = 0     # frames sent to the card since the stream opened
        self.underruns = 0    # blocks we were too late to fill
        self._actions = queue.SimpleQueue()
        self._listeners = []

        try:
            self._stream = sounddevice.OutputStream(
                samplerate=RATE,
                channels=2,
                dtype="float32",
                blocksize=BLOCK,
                # "low" gets a 21 ms buffer, which the Pi's headphone driver
                # cannot keep fed; "high" gets 64 ms and no underruns.
                latency="high",
                device=find_output() if device is None else device,
                callback=self._fill,
            )
            self._stream.start()
        except sounddevice.PortAudioError as exc:
            raise PlaybackError(f"Could not open the audio output: {exc}")

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
        """Seconds from filling a block to hearing it: the card's buffer."""
        return self._stream.latency

    # --- listeners: safe from any thread -----------------------------------

    def listen(self):
        """A new queue that gets every block sent to the jack from now on,
        as (position, frames) - what the recorder adds to a take."""
        sent = queue.SimpleQueue()
        self._listeners = self._listeners + [sent]
        return sent

    def stop_listening(self, sent):
        self._listeners = [listener for listener in self._listeners if listener is not sent]

    # --- actions: safe from any thread -------------------------------------

    def start_metronome(self):
        self._actions.put(lambda now: self.metronome.start(now))

    def stop_metronome(self):
        self._actions.put(lambda now: self.metronome.stop())

    def play(self, track, count_in=0, first_beat=0.0):
        """Play `track` after `count_in` beats of metronome, lined up so the
        track's beat 1 - `first_beat` seconds into the file - lands on the
        beat after the count-in.

        There is no click during the track: a recorded band drifts from a
        perfectly steady metronome, so it is one or the other.
        """
        def action(now):
            if self.track is not None and self.track is not track:
                self.track.pause()
            self.track = track
            if count_in:
                self.metronome.start(now, beats=count_in)
            else:
                self.metronome.stop()
            # Frames between now and the track's first frame. Negative when
            # the file's lead-in is longer than the count-in: then skip into
            # the file instead of starting it in the past.
            lead = round(count_in * self.metronome.frames_per_beat()) - round(first_beat * RATE)
            track.seek(max(-lead, 0))
            track.start(now + max(lead, 0))
        self._actions.put(action)

    def pause(self):
        self._actions.put(lambda now: self.track and self.track.pause())

    def resume(self):
        self._actions.put(lambda now: self.track and self.track.start(now))

    def seek(self, seconds):
        self._actions.put(lambda now: self.track and self.track.seek(round(seconds * RATE)))

    # --- the audio thread --------------------------------------------------

    def _fill(self, out, frames, timing, status):
        if status.output_underflow:
            self.underruns += 1
        while not self._actions.empty():
            self._actions.get_nowait()(self.position)

        out.fill(0)
        if self.track is not None:
            self.track.render(out, self.position)
        self.metronome.render(out, self.position)
        numpy.clip(out, -1.0, 1.0, out=out)
        for listener in self._listeners:
            listener.put((self.position, out.copy()))
        self.position += frames
