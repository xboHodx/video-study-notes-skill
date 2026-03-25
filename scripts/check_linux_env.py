#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))


def _run_via_installed_cli() -> int:
    exe = shutil.which("video-notes") or shutil.which("video-study-notes")
    if not exe:
        print(
            "Could not import local package and `video-notes` is not on PATH. "
            "Install tool via `uv tool install ...` or run from source repository.",
            file=sys.stderr,
        )
        return 1
    cmd = [exe, "check", *sys.argv[1:]]
    return subprocess.run(cmd, check=False).returncode


try:
    from video_study_notes.check_env import main as _module_main
except ModuleNotFoundError:

    def main() -> int:
        return _run_via_installed_cli()

else:

    def main() -> int:
        return _module_main()


if __name__ == "__main__":
    raise SystemExit(main())
