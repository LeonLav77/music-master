"""The backing tracks in a folder, decoded into memory once and kept there.

On start-up the PRELOAD newest files (by modification time - when they
were copied in) are decoded in the background, one at a time. After that,
every track asked for stays in memory too; nothing is ever dropped.

Decoding takes seconds (4 s for a 7-minute song on the Pi), so get()
blocks - call it from a thread, not from the audio callback. A track that
is still waiting in the preload queue is taken out of it and decoded
straight away rather than waiting its turn.

    library = Library("tracks")
    track = library.get("seek_and_destroy.m4a")
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from playback.track import Track, TrackError, decode

PRELOAD = 20
AUDIO = {".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus"}


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

    def get(self, name):
        """The track in file `name`, decoding it first if it is not ready."""
        path = self.folder / name
        # Keep the caller inside the folder - no "../" out of it.
        if path.parent.resolve() != self.folder.resolve() or not path.is_file():
            raise TrackError(f"No such track {name!r}")

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

    def _decode(self, name):
        return Track(name, decode(self.folder / name))
