"""Entry point: build the pipeline and hand it to Qt.

    audio input -> ring buffer -> trigger engine -> renderer -> window
"""

from __future__ import annotations

import argparse
import sys

from audio_input import (
    DEFAULT_BLOCKSIZE,
    DEFAULT_BUFFER_SECONDS,
    MicrophoneInput,
    describe_devices,
)
from trigger import EDGES, RISING, TriggerEngine


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real-time oscilloscope POC")
    parser.add_argument(
        "--list-devices", action="store_true", help="print input devices and exit"
    )
    parser.add_argument(
        "--device",
        default=None,
        help="input device index or name substring (default: system default)",
    )
    parser.add_argument(
        "--samplerate",
        type=float,
        default=None,
        help="capture rate in Hz (default: the device's preferred rate)",
    )
    parser.add_argument(
        "--channels",
        type=int,
        default=1,
        help="channels to capture; 2 turns on the second trace and X-Y",
    )
    parser.add_argument(
        "--blocksize", type=int, default=DEFAULT_BLOCKSIZE, help="PortAudio block size"
    )
    parser.add_argument(
        "--buffer-seconds",
        type=float,
        default=DEFAULT_BUFFER_SECONDS,
        help="ring buffer length in seconds",
    )
    parser.add_argument(
        "--window-ms", type=float, default=20.0, help="initial window length in ms"
    )
    parser.add_argument(
        "--trigger-level", type=float, default=0.0, help="initial trigger level"
    )
    parser.add_argument(
        "--trigger-edge", choices=EDGES, default=RISING, help="initial trigger edge"
    )
    parser.add_argument(
        "--hysteresis",
        type=float,
        default=0.02,
        help="trigger noise rejection band (0 disables it)",
    )
    parser.add_argument(
        "--position",
        type=float,
        default=0.0,
        help="fraction of the window that sits before the edge (0-0.9)",
    )
    parser.add_argument(
        "--holdoff-ms",
        type=float,
        default=0.0,
        help="quiet interval an edge needs behind it to qualify",
    )
    parser.add_argument("--fps", type=int, default=60, help="target redraw rate")
    return parser.parse_args(argv)


def resolve_device(value):
    """Device indices arrive as strings on the command line; names stay strings."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return value


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.list_devices:
        print(describe_devices())
        return 0

    source = MicrophoneInput(
        samplerate=args.samplerate,
        channels=args.channels,
        blocksize=args.blocksize,
        device=resolve_device(args.device),
        buffer_seconds=args.buffer_seconds,
    )
    try:
        source.start()
    except Exception as exc:
        print(f"Could not open the audio input: {exc}", file=sys.stderr)
        print("Run with --list-devices to see what is available.", file=sys.stderr)
        return 1

    engine = TriggerEngine(
        source,
        window_length=round(args.window_ms * source.samplerate / 1000),
        trigger_level=args.trigger_level,
        trigger_edge=args.trigger_edge,
        hysteresis=args.hysteresis,
        position=args.position,
        holdoff_ms=args.holdoff_ms,
    )

    # Imported here so --list-devices works without a display attached.
    from PyQt6.QtWidgets import QApplication

    from main_window import MainWindow

    app = QApplication(sys.argv[:1])

    # The body face, set once on the application so anything that does not
    # ask for a face of its own still gets the house's rather than Qt's.
    import branding as house

    app.setFont(house.body_font())

    # `:focus-visible`, which Qt does not have on its own.
    house.watch_focus(app)

    window = MainWindow(source, engine, fps=args.fps)
    window.show()
    try:
        return app.exec()
    finally:
        source.stop()


if __name__ == "__main__":
    raise SystemExit(main())
