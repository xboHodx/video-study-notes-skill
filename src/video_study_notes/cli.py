from __future__ import annotations

import argparse
import sys
from typing import Callable

from . import __version__
from .check_env import main as check_main
from .extract_keyframes import main as extract_keyframes_main
from .prepare_audio import main as prepare_audio_main


CommandHandler = Callable[[list[str]], int]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-notes",
        description="CLI helpers for the video-study-notes workflow.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("command", nargs="?", help="Subcommand: check | prepare-audio | extract-keyframes")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the selected subcommand.")
    return parser


def _commands() -> dict[str, CommandHandler]:
    return {
        "check": check_main,
        "prepare-audio": prepare_audio_main,
        "extract-keyframes": extract_keyframes_main,
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    parsed = parser.parse_args(argv)
    command = parsed.command

    if not command:
        parser.print_help()
        return 0

    handler = _commands().get(command)
    if handler is None:
        parser.error(f"unknown command: {command}")

    return handler(parsed.args)


if __name__ == "__main__":
    raise SystemExit(main())
