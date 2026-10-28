"""Run the player on its own:

    python -m playback 120                          the metronome
    python -m playback 100 --track song.mp3         a track, after a count-in

Type a new BPM and press Enter to change tempo, `p` to pause or resume the
track, or a time like `1:30` to jump there. Ctrl-C or Ctrl-D stops.
"""

import argparse

from playback.player import Player
from playback.track import Track

parser = argparse.ArgumentParser(prog="python -m playback")
parser.add_argument("bpm", type=float, nargs="?", default=120)
parser.add_argument("--beats", type=int, default=4, help="beats per bar")
parser.add_argument("--volume", type=float, default=1.0, help="metronome, 0 to 1")
parser.add_argument("--track", help="an audio file to play")
parser.add_argument("--count-in", type=int, default=4, help="beats before the track")
parser.add_argument("--first-beat", type=float, default=0.0, help="seconds into the file of the track's beat 1")
parser.add_argument("--track-volume", type=float, default=1.0, help="0 to 1")
parser.add_argument("--device", help="output name or number; default the headphone jack")
args = parser.parse_args()

device = int(args.device) if args.device and args.device.isdigit() else args.device

with Player(device) as player:
    player.metronome.bpm = args.bpm
    player.metronome.beats_per_bar = args.beats
    player.metronome.volume = args.volume
    if args.track:
        track = Track.load(args.track)
        track.volume = args.track_volume
        print(f"{args.track}: {track.duration():.1f} s")
        player.play(track, count_in=args.count_in, first_beat=args.first_beat)
    else:
        player.start_metronome()

    try:
        while True:
            line = input(f"{player.metronome.bpm:g} BPM > ").strip()
            if not line:
                continue
            if line == "p" and player.track is not None:
                if player.track.is_playing():
                    player.pause()
                else:
                    player.resume()
                continue
            if ":" in line:
                minutes, _, seconds = line.partition(":")
                try:
                    player.seek(int(minutes) * 60 + float(seconds))
                except ValueError:
                    print("Type a time like 1:30")
                continue
            try:
                bpm = float(line)
            except ValueError:
                print("Type a BPM like 90, p to pause, or a time like 1:30")
                continue
            if not 20 <= bpm <= 400:
                print("BPM must be between 20 and 400")
                continue
            player.metronome.bpm = bpm
    except (KeyboardInterrupt, EOFError):
        print()
    print(f"Stopped. Underruns: {player.underruns}")
