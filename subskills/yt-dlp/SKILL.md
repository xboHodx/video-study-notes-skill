---
name: yt-dlp
description: Use this skill whenever the user wants to inspect, download, or extract online audio/video with yt-dlp, or asks for YouTube/Bilibili/X/TikTok/media URL downloading, format listing, subtitle fetching, audio extraction, cookies-from-browser, or playlist downloads even if they do not explicitly name yt-dlp.
compatibility:
  tools: ["functions.exec_command"]
  dependencies: ["uv", ".venv/bin/python", "yt-dlp"]
---

# yt-dlp

This subskill is part of the self-contained `video-study-notes` skill. Its helper scripts live under `subskills/yt-dlp/scripts/`, especially `subskills/yt-dlp/scripts/run_yt_dlp.py` for media access and `subskills/yt-dlp/scripts/resolve_project_root.py` for deterministic folder naming.

Prefer the `yt-dlp` installed in the skill-local `.venv`. The wrapper script will try, in order:

- `VIDEO_NOTES_YT_DLP`
- the current Python environment via `python -m yt_dlp`
- the skill-local `.venv/bin/python -m yt_dlp`
- `yt-dlp` from `PATH`

Prefer the Python wrapper script `subskills/yt-dlp/scripts/run_yt_dlp.py` from the main skill directory.

## Workflow

1. Clarify the user's goal:
   - inspect metadata
   - list formats
   - list subtitles
   - download the default best version
   - download a specific format
   - extract audio
   - download a playlist
2. If the request is underspecified, probe before downloading.
3. If `video-study-notes` still needs to decide whether the source is a series / playlist / course, probe metadata first before forcing `--no-playlist`.
4. If the selected URL may collapse a multi-entry container into one visible item, first probe the canonical container URL so `video-study-notes` can retain the series title and choose the correct entry.
5. If the metadata JSON contains multiple entries and the caller wants one note project for one item, pass that item to `resolve_project_root.py` with `--entry-index` or `--video-title` before any download step.
6. Once the project root has been resolved for a single-video workflow, use `--no-playlist` for actual download steps unless the user explicitly asked for playlist behavior.
7. If the caller did not specify an output directory, default to `downloads/yt-dlp/` under the current working directory. When this skill is invoked by `video-study-notes`, always use the explicit per-video subdirectories under the resolved `<workspace_root>/output/...` project root.
8. Prefer explicit output templates so filenames are predictable.
9. After the command finishes, report the saved path or the reason it failed.

## Safe defaults

- Use an explicit `-P` target whenever the parent workflow already chose a per-video project root.
- Use `-o "%(title)s [%(id)s].%(ext)s"` unless the user asked for a different naming scheme.
- Use `--no-playlist` for the download phase by default, not for the initial series / playlist / course probe.
- Use metadata probes first when the correct format is unclear.
- If authentication may be required, first look for the skill-local `cookies.txt` and prefer that over browser cookie extraction.

## First-choice commands

The examples below assume the current directory is the skill root.

Inspect metadata without downloading:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --dump-single-json "<URL>"
```

List available formats:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --no-playlist --list-formats "<URL>"
```

List available subtitles:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --no-playlist --list-subs "<URL>"
```

Download the default best version:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --no-playlist -P downloads/yt-dlp -o "%(title)s [%(id)s].%(ext)s" "<URL>"
```

Download a specific format after checking `--list-formats`:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --no-playlist -f "<FORMAT>" -P downloads/yt-dlp -o "%(title)s [%(id)s].%(ext)s" "<URL>"
```

Extract audio:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --no-playlist -x --audio-format mp3 -P downloads/yt-dlp -o "%(title)s [%(id)s].%(ext)s" "<URL>"
```

Download subtitles without the media file:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --no-playlist --write-subs --write-auto-subs --sub-langs "en.*,zh.*" --skip-download -P downloads/yt-dlp "<URL>"
```

Download a playlist only when requested:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py -P downloads/yt-dlp -o "%(playlist_index)s - %(title)s [%(id)s].%(ext)s" "<PLAYLIST_URL>"
```

Avoid re-downloading items:

```bash
mkdir -p downloads/yt-dlp
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --no-playlist --download-archive downloads/yt-dlp/archive.txt -P downloads/yt-dlp "<URL>"
```

Use browser cookies only when needed:

```bash
.venv/bin/python subskills/yt-dlp/scripts/run_yt_dlp.py --cookies-from-browser chrome --no-playlist "<URL>"
```

## Authentication flow

- If the skill-local `cookies.txt` exists, prefer it over browser cookie extraction.
- The wrapper script automatically adds that `--cookies` argument to remote probes and download commands whenever a cookies-related flag was not passed explicitly.
- Only if that file is absent should you try `--cookies-from-browser`.
- If browser cookie extraction fails with database-copy, decryption, DPAPI, or similar browser-cookie errors, stop retrying the same path and tell the user to export a Netscape-format `cookies.txt` manually to the skill root.
- After the user provides that file, prefer the skill-local relative path for authenticated metadata probes, subtitle probes, and media downloads.

## Decision rules

- If the user asks for "best quality", start with yt-dlp's default format selection. Only add `-f` selectors when there is a clear requirement.
- If the user asks what formats are available, run `--list-formats` first.
- If the user asks whether subtitles exist, run `--list-subs` first.
- If `video-study-notes` needs to choose between `<workspace_root>/output/<Video Title>/` and `<workspace_root>/output/<Series Title>/<Video Title>/`, dump metadata first and resolve the project root before download.
- If a site uses per-entry query parameters such as Bilibili `?p=4`, do not assume the selected URL still exposes the anthology container metadata; probe the canonical container URL first when series grouping matters.
- If the site likely requires login, first check for the skill-local `cookies.txt`. If it is absent, then ask whether to use browser cookies or have the user export `cookies.txt` manually to that path.
- The wrapper auto-attaches the skill-local cookies file to metadata probes, subtitle probes, media downloads, and audio extraction unless the caller already passed explicit auth flags.
- If the task is large or repeatable, prefer `--download-archive`.
- If muxing or audio extraction fails, check whether `ffmpeg` is installed and mention that dependency in the response.

## Constraints

- If no usable subtitle track is available, use the companion skill `media-transcribe` to generate local transcripts from audio.
- Only download content the user is authorized to access.
- Do not assume playlist intent unless the user explicitly asked for playlist behavior.
- Do not add cookies or account-related flags manually unless the task requires them. When a skill-local `cookies.txt` exists, the wrapper handles the common probe/download flows automatically; explicit auth flags still take precedence.

## Reference

Primary documentation: https://github.com/yt-dlp/yt-dlp
