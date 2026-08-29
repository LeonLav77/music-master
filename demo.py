#!/usr/bin/env python3
"""Proof-of-concept demo for talking to a BOSS Katana MkII over USB MIDI.

Run with no arguments to list ports, read the amp's current settings and
briefly change one parameter:

    ./venv/bin/python demo.py

All amp logic lives in katana.py; this file is only a demo/test harness.
"""

import argparse
import sys
import time

import mido

from controls import *
from katana import KatanaError, find_ports


def list_ports():
    """Print every MIDI port, flagging the ones that look like a Katana."""
    print("MIDI output ports:")
    for name in mido.get_output_names():
        mark = "  <-- Katana" if "KATANA" in name.upper() else ""
        print(f"  {name}{mark}")

    print("\nMIDI input ports:")
    for name in mido.get_input_names():
        mark = "  <-- Katana" if "KATANA" in name.upper() else ""
        print(f"  {name}{mark}")

    found = find_ports()
    if len(found) > 1:
        print(
            f"\nNote: the Katana exposes {len(found)} ports; 'MIDI 1' is the "
            "SysEx control port and is what this demo uses."
        )
    print()


def show_panel():
    """Print the amp's current live settings."""
    show_settings()
    print()


def demo_change():
    # gain 100
    set_gain(100)
    
    cry_wah()
    sweep_wah(0, 100, steps=50, delay=0.1)
    sweep_wah(100, 0, steps=50, delay=0.1)
    wah_off()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="MIDI port name (default: autodetect)")
    parser.add_argument("--list", action="store_true", help="list ports and exit")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="only read settings, do not change anything",
    )
    args = parser.parse_args()

    list_ports()
    if args.list:
        return 0

    try:
        amp = connect(args.port)
        print(f"Connected to: {amp.port_name}\n")

        identity = amp.identify()
        print("Identity reply: " + " ".join(f"{b:02X}" for b in identity))
        if len(identity) > 6 and identity[4] == 0x41:
            print("Confirmed a Roland/BOSS device.\n")

        show_panel()

        if not args.read_only:
            demo_change()

        print("Done.")
    except KatanaError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
