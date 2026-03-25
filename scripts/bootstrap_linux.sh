#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This bootstrap script supports Linux only." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it first: https://docs.astral.sh/uv/" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required and must be available on PATH." >&2
  echo "Ubuntu/Debian: sudo apt install -y ffmpeg" >&2
  exit 1
fi

skill_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$skill_root"

if [[ ! -x .venv/bin/python ]]; then
  uv venv .venv
fi

uv pip install --python .venv/bin/python -r requirements-skill.txt

echo
echo "Bootstrap complete."
echo "Skill root: $skill_root"
echo "Next step:"
echo "  cd $skill_root && .venv/bin/python scripts/check_linux_env.py"
