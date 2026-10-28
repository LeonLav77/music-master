"""The backing tracks in a folder, decoded into memory once and kept there.

On start-up the PRELOAD newest files (by modification time - when they
were copied in) are decoded in the background, one at a time. After that,
every track asked for stays in memory too; nothing is ever dropped.

Decoding takes seconds (4 s for a 7-minute song on the Pi), so get()
blocks - call it from a thread, not from the audio callback. A track that
is still waiting in the preload queue is taken out of it and decoded
straight away rather than waiting its turn.

An upload is moved in with add(), which decodes it at once - by the time
the upload is answered, the song is in memory and plays instantly.

    library = Library("tracks")
    track = library.get("seek_and_destroy.m4a")
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from playback.track import Track, TrackError, decode

PRELOAD = 20
AUDIO = {".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus"}
# Uploads are written under this prefix and renamed in when complete, so
# nothing ever sees half a file. Not an AUDIO suffix, so names() skips them.
UPLOAD_PREFIX = ".upload-"


def check_name(name):
    """Refuse a file name that is not a plain audio file name."""
    if Path(name).name != name or name.startswith(".") or Path(name).suffix.lower() not in AUDIO:
        known = ", ".join(sorted(AUDIO))
        raise TrackError(f"{name!r} is not an audio file name ({known})")
    return name


class Library:
    def __init__(self, folder, preload=PRELOAD):
        self.folder = Path(folder)
        self.folder.mkdir(exist_ok=True)
        # name -> Future of its Track: finished ones are the cache, the
        # others are loading or queued.
        self._tracks = {}
        self._lock = threading.Lock()
        self._background = ThreadPoolExecutor(max_workers=1, thread_name_prefix="preload")
        self._now = ThreadPoolExecutor(max_workers=2, thread_name_prefix="load")

        # Left behind by an upload that was cut off when the server stopped.
        for leftover in self.folder.glob(f"{UPLOAD_PREFIX}*"):
            leftover.unlink(missing_ok=True)

        for name in self.names()[:preload]:
            self._tracks[name] = self._background.submit(self._decode, name)

    def close(self):
        self._background.shutdown(wait=False, cancel_futures=True)
        self._now.shutdown(wait=False, cancel_futures=True)

    def names(self):
        """The audio files in the folder, newest first."""
        files = [path for path in self.folder.iterdir()
                 if path.is_file() and path.suffix.lower() in AUDIO]
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return [path.name for path in files]

    def is_ready(self, name):
        future = self._tracks.get(name)
        return future is not None and future.done() and future.exception() is None

    def _existing(self, name):
        path = self.folder / name
        # Keep the caller inside the folder - no "../" out of it.
        if path.parent.resolve() != self.folder.resolve() or not path.is_file():
            raise TrackError(f"No such track {name!r}")
        return path

    def get(self, name):
        """The track in file `name`, decoding it first if it is not ready."""
        self._existing(name)
        with self._lock:
            future = self._tracks.get(name)
            # cancel() only succeeds for one still queued, not yet started.
            if future is None or future.cancel():
                future = self._now.submit(self._decode, name)
                self._tracks[name] = future
        try:
            return future.result()
        except TrackError:
            # Forget the failure, so a file that was still being copied in
            # can be tried again.
            with self._lock:
                if self._tracks.get(name) is future:
                    del self._tracks[name]
            raise

    def upload_path(self):
        """A fresh temporary path in the folder to write an upload to."""
        return self.folder / f"{UPLOAD_PREFIX}{os.urandom(6).hex()}.part"

    def add(self, source, name):
        """Move the finished upload `source` in as `name` - as "name (2)" if
        that is taken, so nothing is overwritten - and start decoding it
        straight away. Returns the name used and the Future of its Track."""
        check_name(name)
        stem, suffix = Path(name).stem, Path(name).suffix
        with self._lock:
            final, number = name, 2
            while (self.folder / final).exists():
                final, number = f"{stem} ({number}){suffix}", number + 1
            # Same folder, so a rename: the file appears whole or not at all.
            os.replace(source, self.folder / final)
            future = self._now.submit(self._decode, final)
            self._tracks[final] = future
        return final, future

    def remove(self, name):
        """Delete the file and forget its track."""
        path = self._existing(name)
        with self._lock:
            future = self._tracks.pop(name, None)
            if future is not None:
                future.cancel()
            path.unlink()

    def _decode(self, name):
        return Track(name, decode(self.folder / name))
