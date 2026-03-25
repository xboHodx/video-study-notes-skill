#!/usr/bin/env python3
from __future__ import annotations

import ctypes.util
import platform
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON = SKILL_ROOT / ".venv" / "bin" / "python"


def print_status(label: str, detail: str) -> None:
    print(f"[{label}] {detail}")


def main() -> int:
    failures = 0

    if platform.system() != "Linux":
        print_status("FAIL", f"Linux is required, current platform is {platform.system()}.")
        return 1
    print_status("OK", f"Platform: {platform.platform()}")
    print_status("OK", f"Python: {sys.executable}")
    print_status("OK", f"Skill root: {SKILL_ROOT}")

    current_python = Path(sys.executable)
    if current_python != EXPECTED_PYTHON:
        print_status(
            "WARN",
            f"Expected to run with {EXPECTED_PYTHON}, but current interpreter is {current_python}. "
            "Prefer `.venv/bin/python scripts/check_linux_env.py` from the skill root.",
        )

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print_status("OK", f"ffmpeg found at {ffmpeg}")
    else:
        print_status("FAIL", "ffmpeg is missing from PATH")
        failures += 1

    try:
        import yt_dlp  # noqa: F401
    except Exception as exc:
        print_status("FAIL", f"Python package yt-dlp is not importable: {exc}")
        failures += 1
    else:
        print_status("OK", "Python package yt-dlp is importable")

    try:
        import faster_whisper  # noqa: F401
    except Exception as exc:
        print_status("FAIL", f"Python package faster-whisper is not importable: {exc}")
        failures += 1
    else:
        print_status("OK", "Python package faster-whisper is importable")

    nvidia_smi = shutil.which("nvidia-smi")
    cublas = ctypes.util.find_library("cublas")
    if nvidia_smi:
        print_status("OK", f"nvidia-smi found at {nvidia_smi}")
        try:
            output = subprocess.run(
                [nvidia_smi, "--query-gpu=name,driver_version", "--format=csv,noheader"],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception as exc:
            print_status("WARN", f"Unable to query NVIDIA GPU details: {exc}")
        else:
            details = output.stdout.strip() or output.stderr.strip() or "query returned no details"
            print_status("INFO", f"NVIDIA GPUs: {details}")
    else:
        print_status("INFO", "nvidia-smi not found; GPU acceleration will not be used")

    if cublas:
        print_status("OK", f"CUDA cublas library detected: {cublas}")
    else:
        print_status("INFO", "CUDA cublas library not detected; CPU mode remains available")

    if failures:
        print_status("FAIL", "Environment is not ready for CPU mode.")
        print("From the skill root, run: bash scripts/bootstrap_linux.sh")
        return 1

    if nvidia_smi and cublas:
        print_status("OK", "CPU mode ready; GPU mode should be available and will still be verified at runtime.")
    else:
        print_status("OK", "CPU mode ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
