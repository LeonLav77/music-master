"""Playing backing tracks out the analog jack, into the amp's AUX IN.

This module is the audio half of the rig and knows nothing about MIDI. It
is the Python form of scripts/aux-play.sh, which stays as the hand tool -
the reasoning about *why* AUX rather than USB lives there and is not
repeated here.

The one thing worth restating, because everything below depends on it: the
Katana's USB input lands at the *input* stage, so a track sent there gets
re-amped and kills the guitar jack. AUX IN mixes in after the modelling.
`pick_sink` therefore refuses to guess the USB device even when it is the
only one present.

Three things happen here:

  * finding a track on disk and reading its duration
  * generating a count-in click and gluing it to the front of a track
  * running pw-play as a child process, with pause and seek on top

pw-play has neither pause nor seek - it plays a file from its start to its
end and exits. Both are built here rather than by switching to a library
with a real audio API: the tradeoffs are noted at `Player.pause` and
`Player.seek`, and both are cheap enough at this scale to be worth the
absence of a dependency.
"""

import json
import math
import re
import shutil
import struct
import contextlib
import subprocess
import signal
import tempfile
import threading
import time
import wave
from pathlib import Path


class AudioError(Exception):
    """Anything that stops a track reaching the amp."""


# Audio we can hand to pw-play. Deliberately narrow: these are what ffmpeg
# on a stock Pi decodes without extra codecs, and what yt-dlp is asked for.
TRACK_SUFFIXES = (".wav", ".flac", ".mp3", ".ogg", ".opus", ".m4a")

# The click is written at CD rate; ffmpeg resamples the pair when they are
# joined, so this never has to match the track.
CLICK_RATE = 44100

# How far the deck will push a track above its own level, in dB.
#
# 12 dB is roughly four times as loud and is where the limiter starts
# audibly squashing a dense mix - past that you are not making the track
# louder, only flatter. Nothing here stops you turning the amp up instead,
# which is always the better answer when it is available.
MAX_BOOST_DB = 12.0

# Peak ceiling for the limiter, as a fraction of full scale. Just under 1.0
# so that the resampling on the way out cannot overshoot into a clip.
LIMIT = 0.97


# --- Devices ---------------------------------------------------------------

def _pw_nodes():
    """Every PipeWire sink node name, or an empty list if pw-cli is absent."""
    if shutil.which("pw-cli") is None:
        return []
    try:
        out = subprocess.run(
            ["pw-cli", "ls", "Node"], capture_output=True, text=True, timeout=5
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return []
    return re.findall(r'(?:alsa_output|bluez_output)[^"]*', out)


def sinks():
    """Candidate output devices, best first.

    The Katana's own USB audio is listed but flagged: it is a real sink and
    hiding it would look like a bug, but choosing it re-amps the track.
    """
    found = []
    for name in dict.fromkeys(_pw_nodes()):
        katana = "KATANA" in name.upper()
        hdmi = "hdmi" in name.lower()
        found.append({
            "name": name,
            "analog": name.startswith("alsa_output") and not hdmi and not katana,
            "reamps": katana,
        })
    # Analog first, then the rest; the USB amp input sorts last.
    found.sort(key=lambda s: (s["reamps"], not s["analog"]))
    return found


def pick_sink(preferred=None):
    """Choose where to play, mirroring aux-play.sh's rules.

    A preferred name is honoured if it is really there - a stale one from a
    saved setting must not silently play somewhere else. Otherwise the first
    analog sink wins. We never fall back to the *default* sink: that follows
    whatever connected last, so a pair of Bluetooth headphones would quietly
    steal a track meant for the amp.
    """
    available = sinks()
    if not available:
        raise AudioError(
            "No audio outputs found. Is PipeWire running?"
        )

    if preferred:
        for sink in available:
            if sink["name"] == preferred:
                return sink["name"]
        raise AudioError(f"Output {preferred!r} is not connected")

    for sink in available:
        if sink["analog"]:
            return sink["name"]

    raise AudioError(
        "No analog output found. Set one explicitly - the only sinks present "
        "are HDMI, Bluetooth, or the Katana's USB input (which re-amps)."
    )


# --- Tracks ----------------------------------------------------------------

def duration(path):
    """Length of an audio file in seconds, or None if ffprobe cannot say."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    try:
        return round(float(out.stdout.strip()), 2)
    except ValueError:
        return None


def scan(directory):
    """Every playable file in `directory`, newest first.

    Durations come from ffprobe, one subprocess per file. That is fine for a
    shelf of backing tracks and would not be for a music library; if this
    ever grows one, the answer is a cache keyed on (path, mtime), not a
    faster probe.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []

    tracks = []
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.lower() not in TRACK_SUFFIXES:
            continue
        stat = path.stat()
        tracks.append({
            "name": path.stem,
            "file": path.name,
            "duration": duration(path),
            "size": stat.st_size,
            "added": stat.st_mtime,
        })
    tracks.sort(key=lambda t: t["added"], reverse=True)
    return tracks


# --- Count-in --------------------------------------------------------------

def write_click(path, bpm, beats, accent_every=4):
    """Write a click track: `beats` blips at `bpm`, accented on the downbeat.

    Hand-written PCM through the stdlib `wave` module rather than ffmpeg's
    sine generator. It is a page of arithmetic either way, and this keeps
    the count-in - the one thing that has to be rhythmically exact - out of
    reach of ffmpeg's filter-graph rounding.

    Each blip is a decaying sine: 1760 Hz on the accent, 880 Hz elsewhere,
    which is audible against a loud backing track without being shrill.
    """
    if bpm <= 0:
        raise AudioError("BPM must be positive")
    if beats <= 0:
        raise AudioError("A count-in needs at least one beat")

    seconds_per_beat = 60.0 / bpm
    # Round the total to a whole frame so the file length is exactly
    # beats * seconds_per_beat - the click has to line up with the track.
    total_frames = int(round(CLICK_RATE * seconds_per_beat * beats))
    frames_per_beat = CLICK_RATE * seconds_per_beat

    # 80 ms of blip, then silence until the next beat.
    blip = 0.08

    # Silence first, then paint each blip over it. Only the first 80 ms of
    # every beat carries any signal, so synthesising the gaps sample by
    # sample was most of the work: at the widest settings the endpoint
    # accepts (8 bars of 12/8 at 30 bpm) that loop ran 8.5M times and took
    # nearly two seconds, all of it while the playback lock was held.
    data = bytearray(total_frames * 4)
    blip_frames = int(blip * CLICK_RATE)

    for beat in range(beats):
        freq = 1760.0 if beat % accent_every == 0 else 880.0
        start = int(round(beat * frames_per_beat))
        for i in range(min(blip_frames, total_frames - start)):
            t = i / CLICK_RATE
            # Exponential decay: a click, not a tone.
            envelope = math.exp(-t * 40.0)
            sample = int(0.5 * envelope * math.sin(2 * math.pi * freq * t) * 32767)
            struct.pack_into("<hh", data, (start + i) * 4, sample, sample)

    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(CLICK_RATE)
        out.writeframes(bytes(data))
    return path


def _gain_filter(db):
    """ffmpeg filter for `db` of make-up gain, peaks caught by a limiter.

    A backing track sits under the guitar at unity, which is right when you
    are practising alone and quiet when someone else is in the room. The
    obvious fix - multiply the samples - does not work on modern masters:
    they already peak at full scale, so anything above 1.0 is clipped
    rather than amplified. Measured on a track from this library, a plain
    +6 dB drove 6.3% of samples into hard clipping.

    So the gain goes through a limiter, which turns the level up and then
    catches the peaks that would have clipped. That costs a little dynamic
    range - loud passages are squashed toward the quiet ones - which is the
    honest trade: a backing track needs to be heard over a band, not to
    win an audiophile argument.

    Returns "" for no boost, so the caller can drop the filter entirely
    and leave the audio untouched.
    """
    if not db:
        return ""
    return (
        f"volume={db:.2f}dB,"
        f"alimiter=level_in=1:level_out={LIMIT}:limit={LIMIT}:attack=5:release=50"
    )


def boost(track, destination, db):
    """Copy `track` to `destination`, `db` louder and limited.

    Not used by playback, which streams the same filter through a pipe so
    it does not have to wait for a whole file to be written (see
    `Player._spawn`). This is the offline form: useful for rendering a
    louder copy to keep, and for checking what the filter actually does to
    a track without having to listen to it.
    """
    if shutil.which("ffmpeg") is None:
        raise AudioError("ffmpeg is needed to boost the level but is not installed")
    if not 0 <= db <= MAX_BOOST_DB:
        raise AudioError(f"Boost must be between 0 and {MAX_BOOST_DB:g} dB")

    # anull for db=0: ffmpeg rejects an empty filter graph, and a copy at
    # no gain is a legal thing to ask for even if play() never does.
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(track),
         "-af", _gain_filter(db) or "anull",
         "-ar", str(CLICK_RATE), "-ac", "2", str(destination)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AudioError(f"Could not raise the level: {result.stderr.strip()}")
    return destination


def trim(track, destination, start):
    """Copy `track` from `start` seconds in. Used to fake a seek.

    `-ss` before `-i` seeks by container index rather than decoding up to
    the point, which is what makes this fast enough to sit behind a scrub
    bar. `-c copy` is safe here, unlike in the concat above: one input, so
    there is no second format to reconcile.
    """
    if shutil.which("ffmpeg") is None:
        raise AudioError("ffmpeg is needed to seek but is not installed")

    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}",
         "-i", str(track), "-c", "copy", str(destination)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AudioError(f"Could not seek: {result.stderr.strip()}")
    return destination


# --- Playback --------------------------------------------------------------

class Player:
    """One pw-play child process, with the transport controls it lacks.

    Only one track plays at a time - a second would mix into the same amp
    input, which is never what anyone wanted. Starting a new one stops the
    old one.

    Position is *inferred* from the clock rather than read back from the
    player, because pw-play reports nothing. That makes it accurate to
    within the audio buffer, which is inaudible here and would not be good
    enough for anything that had to stay in sync with something else.
    """

    def __init__(self):
        self._process = None
        self._sink = None
        self._track = None          # what the caller asked for
        self._source = None         # its path on disk
        self._playing_file = None   # what is actually on disk being played
        self._temp = None           # scratch dir, when count-in or seek made a file
        self._started = 0.0         # monotonic, when the current run began
        self._offset = 0.0          # seconds of the track already behind us
        self._paused_at = None
        self._duration = None
        self._lead_in = 0.0         # count-in seconds sitting before the track
        self._volume = 1.0          # remembered, so a seek does not reset it
        self._db = 0.0              # ditto for the boost
        self._click = None          # the count-in's own pw-play child
        self._starter = None        # timer that starts the track after it
        self._encoder = None        # ffmpeg feeding pw-play, when boosting
        self._encoder_log = None    # its stderr, kept for the error message
        self._last_error = None     # why the last track stopped, if it failed
        # The count-in runs the transport from a timer thread, so the few
        # fields it touches need guarding against a stop() arriving from
        # the request thread at the same moment.
        self._lock = threading.RLock()

    # -- state --

    @property
    def active(self):
        """Is anything alive - the count-in, the track, playing or paused?

        The count-in is a second process, and during it `_process` is still
        None: the transport is very much running, so both have to count.
        """
        for proc in (self._process, self._click):
            if proc is not None and proc.poll() is None:
                return True
        # A pending timer is also "active": the click may have drained but
        # the track it schedules has not started yet.
        return self._starter is not None

    @property
    def paused(self):
        return self.active and self._paused_at is not None

    @property
    def playing(self):
        return self.active and self._paused_at is None

    def position(self):
        """Seconds into the *track*, negative during the count-in."""
        if not self.active:
            return 0.0
        end = self._paused_at if self._paused_at is not None else time.monotonic()
        return (end - self._started) + self._offset - self._lead_in

    def status(self):
        """Everything a UI needs to draw the transport."""
        # Read the encoder's failure before reaping: _reap() clears the
        # handles on a dead track, and the explanation would go with them.
        failure = self.encoder_error()
        self._reap()
        if failure:
            self._last_error = failure
        return {
            "state": "paused" if self.paused else "playing" if self.playing else "stopped",
            "track": self._track,
            "position": round(max(0.0, self.position()), 2),
            "duration": self._duration,
            "counting_in": self.active and self.position() < 0,
            "count_in_remaining": (
                round(-self.position(), 2) if self.active and self.position() < 0 else 0.0
            ),
            "sink": self._sink,
            "boost_db": self._db,
            # Sticky until the next play: a track that died two polls ago
            # still has to explain itself, and by then the process is gone.
            "error": self._last_error,
        }

    def encoder_error(self):
        """Why a boosted track stopped early, if ffmpeg is what failed.

        The streaming boost puts ffmpeg in front of pw-play, so a file it
        cannot decode kills playback with no exception anywhere - the play
        request has long since returned 200. This is how that failure gets
        a message instead of the track simply never being heard.

        Returns None when nothing is wrong, which includes the normal case
        of ffmpeg being killed by a stop.
        """
        if self._encoder is None or self._encoder_log is None:
            return None
        code = self._encoder.poll()
        # Still running, exited cleanly, or terminated by us on a stop.
        if code is None or code == 0 or code < 0:
            return None
        try:
            self._encoder_log.flush()
            text = Path(self._encoder_log.name).read_text().strip()
        except OSError:
            return None
        if not text:
            return f"The track could not be decoded (ffmpeg exit {code})"
        return text.splitlines()[-1]

    def _reap(self):
        """Drop the handle once the track has played out.

        Called from status() rather than from a timer: the only thing that
        cares whether a finished track is still "playing" is something
        asking, and this way an idle server does no work at all.
        """
        # Only the track ending means the transport is done. During the
        # count-in `_process` is None and a pending `_starter` is what says
        # the track is still coming; reaping on that would tear the whole
        # thing down between the click and the downbeat.
        if self._process is None:
            return
        if self._process.poll() is not None:
            self._cleanup()

    def _cleanup(self):
        """Return to a stopped transport, whatever got us here.

        Clears the loaded track as well as the process. A track that has
        played out is not "still loaded, just not running": leaving the
        name and duration behind made a finished track look paused to
        status(), and let seek() pass its own guard and restart something
        the listener had already heard to the end.
        """
        self._process = None
        self._click = None
        self._starter = None
        self._encoder = None
        if self._encoder_log is not None:
            with contextlib.suppress(OSError):
                self._encoder_log.close()
                Path(self._encoder_log.name).unlink()
            self._encoder_log = None
        self._playing_file = None
        self._paused_at = None
        self._offset = 0.0
        self._lead_in = 0.0
        self._track = None
        self._source = None
        self._duration = None
        self._db = 0.0
        if self._temp is not None:
            shutil.rmtree(self._temp, ignore_errors=True)
            self._temp = None

    # -- transport --

    def play(self, track, sink=None, volume=1.0, count_in=None, start=0.0, db=0.0):
        """Start `track`. Any current track stops.

        `count_in` is (bpm, beats, accent_every) or None. The click is
        played as its own short file and the track is started on a timer
        when it ends, rather than being glued to the front of the track.

        Gluing was the obvious implementation and it was far too slow. It
        meant decoding and re-encoding the whole song to prepend two
        seconds of click: cost scaled with track length, so a seven-minute
        backing track wrote 73 MB of WAV and took most of a second before
        anything was audible. Playing them in sequence is independent of
        length - the click is a tenth of a megabyte whatever the song is,
        and the track itself is handed to pw-play untouched.

        The two never overlap, so there is no mixing and nothing to drift:
        the second process is started when the first one's audio is due to
        finish, timed from a monotonic clock rather than from the click
        process exiting (pw-play lingers ~130 ms after its last sample
        while its buffer drains, which would push the downbeat late).

        `volume` is passed to pw-play unchanged. aux-play.sh explains why it
        should stay at unity: the analog jack is low-power, the amp's AUX IN
        wants line level, and pushing past 1.0 clips rather than getting
        louder. Balance against the guitar on the amp, not here.

        `db` is the other half of that. Where `volume` only attenuates, this
        raises the track above its own recorded level for playing with other
        people, by rebuilding the audio through a limiter - see
        `_gain_filter`. This one genuinely does have to rewrite the audio,
        so it still costs an ffmpeg pass proportional to track length; it
        is a deliberate setting rather than a fader for exactly that reason.
        """
        track = Path(track)
        if not track.is_file():
            raise AudioError(f"No such track: {track.name}")
        if shutil.which("pw-play") is None:
            raise AudioError("pw-play is not installed (PipeWire tools missing)")
        if not 0.0 <= volume <= 1.0:
            raise AudioError("Volume must be between 0.0 and 1.0")
        if not 0 <= db <= MAX_BOOST_DB:
            raise AudioError(f"Boost must be between 0 and {MAX_BOOST_DB:g} dB")

        self.stop()

        target = pick_sink(sink)
        length = duration(track)
        source = track
        lead_in = 0.0
        temp = None

        # A scratch dir only when something actually has to be written.
        # Note what is *not* here any more: the track itself, for a plain
        # count-in. Only a seek (a container-level copy) or a boost (a real
        # re-encode) touches the audio now.
        if start > 0 or count_in or db:
            temp = Path(tempfile.mkdtemp(prefix="katana-aux-"))

        click_file = None
        try:
            if start > 0:
                if length is not None and start >= length:
                    raise AudioError("Cannot start past the end of the track")
                # With a boost, ffmpeg is already in the pipeline and does
                # the seek itself; without one, a container-level copy is
                # the cheapest way to start partway in.
                if not db:
                    source = trim(source, temp / f"seek{track.suffix}", start)

            if count_in:
                bpm, beats, accent = count_in
                lead_in = beats * (60.0 / bpm)
                # Cheap and independent of the track: a couple of seconds
                # of PCM, written in about ten milliseconds.
                click_file = write_click(temp / "click.wav", bpm, beats, accent)
        except Exception:
            if temp is not None:
                shutil.rmtree(temp, ignore_errors=True)
            raise

        # Everything from here touches fields the count-in timer also
        # reads, so it happens under the lock. The timer can fire while
        # this method is still running - on a loaded machine, or simply
        # with a very short count-in - and half-written transport state is
        # how a track ends up playing at the wrong volume or not at all.
        with self._lock:
            self._last_error = None
            self._sink = target
            self._track = track.name
            self._source = track
            self._playing_file = source
            self._temp = temp
            self._duration = length
            self._lead_in = lead_in
            self._volume = volume
            self._db = db
            self._offset = start
            self._paused_at = None
            self._started = time.monotonic()

            try:
                if click_file is not None:
                    self._click = self._spawn(click_file, target, volume)
                    # Timed from the clock, not from the click process
                    # exiting: pw-play hangs around after its last sample
                    # while the buffer drains, and waiting for that would
                    # put the downbeat roughly 130 ms late every time.
                    timer = threading.Timer(
                        lead_in, self._start_track,
                        (source, target, db, start),
                    )
                    timer.daemon = True
                    self._starter = timer
                    timer.start()
                else:
                    self._process = self._spawn(source, target, volume, db, start)
            except OSError as exc:
                self._cleanup()
                raise AudioError(f"Could not start playback: {exc}") from exc

            return self.status()

    def _spawn(self, path, target, volume, db=0.0, start=0.0):
        """One pw-play child, with its output discarded.

        stdout and stderr go to /dev/null rather than a pipe: nothing ever
        reads them, so a pipe would leak a descriptor per play and, if
        pw-play ever did get chatty, fill its buffer and wedge the track
        mid-song. Failures surface as an exit status, which _reap() notices.

        With a boost, ffmpeg is put in front of pw-play as a pipe rather
        than writing a processed copy first. Same filter either way; the
        difference is that a pipe starts playing while the encode is still
        running, so startup stops scaling with track length - measured on a
        seven-minute song, 40 ms instead of 1.1 s. A seek is handled by
        ffmpeg's own -ss so the pipe still starts in the right place.
        """
        if not db:
            return subprocess.Popen(
                ["pw-play", "--target", target, "--volume", f"{volume:.3f}", str(path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

        seek = ["-ss", f"{start:.3f}"] if start > 0 else []
        # ffmpeg's stderr goes to a file rather than a pipe or /dev/null:
        # a pipe nobody drains would eventually block the encoder, and
        # /dev/null threw away the only explanation of a failed decode.
        # _encoder_error() reads it back when a boosted track dies early.
        self._encoder_log = tempfile.NamedTemporaryFile(
            prefix="katana-ffmpeg-", suffix=".log", delete=False
        )
        encoder = subprocess.Popen(
            ["ffmpeg", "-v", "error", *seek, "-i", str(path),
             "-af", _gain_filter(db),
             "-f", "wav", "-ar", str(CLICK_RATE), "-ac", "2", "-"],
            stdout=subprocess.PIPE, stderr=self._encoder_log,
        )
        player = subprocess.Popen(
            ["pw-play", "--target", target, "--volume", f"{volume:.3f}", "-"],
            stdin=encoder.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        # Our copy of the pipe has to go, or ffmpeg never sees pw-play exit
        # and the encoder lingers after the track is stopped.
        encoder.stdout.close()
        self._encoder = encoder
        return player

    def _start_track(self, source, target, db=0.0, start=0.0):
        """Start the track once the count-in has played. Runs on a timer.

        Checks that it is still the *current* timer, by identity, not just
        that some timer is pending. Timer.cancel() cannot recall a callback
        that has already begun running, so a stop - or a second play that
        installed its own count-in - can leave this blocked on the lock
        with its work already obsolete. Comparing against `_starter` catches
        both: a stop clears it, and a new play replaces it, so in either
        case this returns without starting a track nobody is waiting for.

        The volume is read from the player rather than captured when the
        timer was scheduled, so moving the fader during the count-in
        applies to the track when it starts.
        """
        with self._lock:
            # A threading.Timer is itself the thread it runs on, so the
            # timer that is executing right now is current_thread().
            if self._starter is not threading.current_thread():
                return
            self._starter = None
            try:
                self._process = self._spawn(
                    source, target, self._volume, db, start
                )
            except OSError:
                # Nothing to raise to - we are on a timer thread. The
                # transport simply reads as stopped on the next status().
                self._cleanup()

    def set_volume(self, volume):
        """Change the level of the track already playing.

        pw-play takes `--volume` once at start-up and offers no way to
        change it afterwards, so this goes around it: PipeWire exposes the
        running stream as a node, and wpctl can set that node's volume
        live. Without this the level fader did nothing until the next
        track - the readout moved and the sound did not.

        Silently does nothing if wpctl is missing or the node cannot be
        found. A level control that fails loudly mid-song would be worse
        than one that misses an adjustment; the value is still remembered
        and applied on the next play.
        """
        if not 0.0 <= volume <= 1.0:
            raise AudioError("Volume must be between 0.0 and 1.0")
        with self._lock:
            self._volume = volume
            if not self.active or shutil.which("wpctl") is None:
                return False

            # During the count-in there is no track stream to adjust yet.
            # That is not a failure - _start_track reads `_volume` when it
            # fires, so the change lands on the track the moment it begins
            # - but it has not been applied to anything *now*, and saying
            # otherwise would make a fader look like it worked when the
            # click carried on at the old level.
            nodes = self._stream_nodes()
            if not nodes:
                return False

            for node in nodes:
                subprocess.run(["wpctl", "set-volume", node, f"{volume:.3f}"],
                               capture_output=True)
            return True

    def _stream_nodes(self):
        """PipeWire node ids belonging to our pw-play child.

        Matched on the process id rather than the name: another pw-play on
        the machine is somebody else's audio, and turning it down would be
        a surprising thing for a guitar amp UI to do.
        """
        # Both children: during the count-in only the click exists, and it
        # should follow the fader like anything else coming out of the jack.
        pids = {p.pid for p in (self._process, self._click)
                if p is not None and p.poll() is None}
        if not pids:
            return []
        try:
            dump = subprocess.run(["pw-dump"], capture_output=True, text=True,
                                  timeout=5).stdout
            objects = json.loads(dump)
        except (subprocess.SubprocessError, OSError, ValueError):
            return []

        # Two hops. Only the Client object carries the process id; the
        # audio Stream that actually has a volume is a separate object
        # pointing back at that client. Matching the pid alone finds the
        # client, whose "volume" wpctl will happily accept and silently do
        # nothing with.
        clients = {
            str(obj["id"]) for obj in objects
            if ((obj.get("info") or {}).get("props") or {})
            .get("application.process.id") in pids
        }
        if not clients:
            return []

        return [
            str(obj["id"]) for obj in objects
            if str((((obj.get("info") or {}).get("props") or {})
                    .get("client.id"))) in clients
            and str((((obj.get("info") or {}).get("props") or {})
                     .get("media.class"))).startswith("Stream/Output")
        ]

    def pause(self):
        """Hold the track where it is.

        SIGSTOP freezes the process mid-buffer, so the sound stops within
        the ~100 ms pw-play has already handed to the graph. Nothing is
        flushed, which is why resuming is seamless - and also why this is
        pause rather than a real stop: a stopped process cannot be resumed
        into the same audio stream.
        """
        with self._lock:
            if not self.playing:
                return self.status()
            # Pausing during the count-in stops the whole gesture rather
            # than freezing a click mid-blip: a count-in you resume three
            # bars later has not counted you into anything.
            if self._starter is not None or (
                self._click is not None and self._click.poll() is None
            ):
                return self.stop()
            self._process.send_signal(signal.SIGSTOP)
            self._paused_at = time.monotonic()
            return self.status()

    def resume(self):
        with self._lock:
            # Only a paused track can resume, and pause() only ever pauses
            # a track - a count-in is stopped rather than frozen - so
            # `_process` is always the thing to wake here.
            if not self.paused or self._process is None:
                return self.status()
            # Everything between the pause and now is time the track did
            # not advance, so roll the start forward by exactly that much.
            self._started += time.monotonic() - self._paused_at
            self._paused_at = None
            self._process.send_signal(signal.SIGCONT)
            return self.status()

    def stop(self):
        """Stop everything: the track, the count-in, and a pending start.

        The timer is cancelled first and under the lock. Cancelling a
        threading.Timer that has already fired does nothing, so `_starter`
        is also the flag `_start_track` checks - clearing it here is what
        stops a click that is mid-drain from starting the track a moment
        after the user pressed stop.
        """
        with self._lock:
            starter, self._starter = self._starter, None
            if starter is not None:
                starter.cancel()

            for proc in (self._click, self._process, self._encoder):
                if proc is None or proc.poll() is not None:
                    continue
                # A paused process ignores SIGTERM until it runs again, so
                # wake it first - otherwise stopping a paused track hangs.
                if self._paused_at is not None:
                    proc.send_signal(signal.SIGCONT)
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)

            self._cleanup()
            return self.status()

    def seek(self, position, **kwargs):
        """Jump to `position` seconds by restarting from a trimmed copy.

        pw-play cannot seek, so this is a stop and a fresh start. It costs
        one ffmpeg trim - tens of milliseconds, since `-ss` before `-i`
        seeks the container instead of decoding - which is under the
        threshold where a scrub feels broken. It is emphatically not
        sample-accurate, and dragging the bar restarts the process each
        time, so callers should scrub on release rather than continuously.

        The count-in is deliberately not rebuilt: it counts you into the
        top of a track, and hearing four beats before landing halfway
        through one is not what anybody meant by scrubbing there.
        """
        if self._source is None:
            raise AudioError("Nothing is playing")
        # Carry the current sink and level across the restart. Without the
        # volume the play() default of 1.0 would apply, and scrubbing a
        # quiet backing track would slam it to full into the amp's AUX IN.
        kwargs.setdefault("sink", self._sink)
        kwargs.setdefault("volume", self._volume)
        kwargs.setdefault("db", self._db)
        return self.play(self._source, start=max(0.0, position), **kwargs)
