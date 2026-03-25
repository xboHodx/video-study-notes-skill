---
name: video-study-notes
description: Use this skill whenever the user wants to turn a video URL or a local video file into local study notes, including reusing existing subtitles when available, transcribing only when no usable subtitle text exists, extracting keyframes, and producing a concise Markdown learning note with embedded screenshots. If the input is a link, run the probe/download flow. If the input is a local video file, skip downloading and work from the local media plus any sidecar subtitle files.
compatibility:
  tools: ["functions.exec_command", "functions.view_image"]
  dependencies: ["uv", ".venv/bin/python", "ffmpeg", "yt-dlp", "faster-whisper"]
---

# video-study-notes

This skill is self-contained under its own skill directory. In this workspace the canonical path is `.agent/skills/video-study-notes/`, and `.codex/skills/video-study-notes/` resolves there as a compatibility symlink.

Reuse the bundled companion skills instead of re-deriving their workflows:

- Read `subskills/yt-dlp/SKILL.md` for media download, subtitle probing, cookies, and authenticated access.
- Read `subskills/media-transcribe/SKILL.md` when no usable subtitle track is available and a transcription fallback is needed.

The main skill keeps only project-wide helpers under `scripts/`:

- `scripts/extract_keyframes.py`
- `scripts/prepare_audio.py`
- `scripts/bootstrap_linux.sh`
- `scripts/check_linux_env.py`

Subskill-specific helpers live with their subskills:

- `subskills/yt-dlp/scripts/run_yt_dlp.py`
- `subskills/yt-dlp/scripts/resolve_project_root.py`
- `subskills/media-transcribe/scripts/transcribe_audio.py`
- `subskills/media-transcribe/scripts/find_local_subtitles.py`

## Goal

Given one video source, build a local note project that:

1. resolves a deterministic project root before creating any directories
2. reuses existing subtitle text when available
3. falls back to local transcription only if no usable subtitle text exists
4. extracts candidate screenshots from scene changes and important timestamps
5. has the model review those candidate screenshots and keep the most informative ones
6. produces one concise, high-signal Markdown note with images placed near the relevant explanation

## Linux prerequisites

This skill is intended to run on Linux machines and must use `uv` to manage the environment stored in the skill-local `.venv`.

Minimum system dependencies:

- `python3`
- `ffmpeg`
- `uv`

Recommended bootstrap flow from the repo root:

```bash
cd .agent/skills/video-study-notes
sudo apt install -y python3 python3-venv ffmpeg
bash scripts/bootstrap_linux.sh
.venv/bin/python scripts/check_linux_env.py
```

Notes:

- CPU mode is the portability baseline and should work on ordinary Linux machines.
- NVIDIA GPU acceleration is optional. If CUDA initialization fails, the transcription script falls back to CPU automatically.
- Keep the virtual environment inside this skill directory and manage it with `uv`.

## Project root selection

Before creating any directories, resolve the folder layout first.

1. Use `subskills/yt-dlp/scripts/resolve_project_root.py` to sanitize names and compute the project root.
   - unless the caller overrides `--output-base`, the default base directory is `<workspace_root>/output/`, where `<workspace_root>` is the parent directory of the nearest `.agent` or `.codex` directory
2. If the source is a series / playlist / course, use the series title as the first-level folder and the video title as the second-level folder:
   - `<workspace_root>/output/<Series Title>/<Video Title>/`
   - when the metadata is a multi-entry container, pass `--entry-index` for the selected item or pass its title explicitly with `--video-title`
3. If the source is not a series, use the video title as the first-level folder:
   - `<workspace_root>/output/<Video Title>/`
4. Never improvise a different folder convention once the script has resolved the root.

Use human-readable names, but strip or replace path separators, control characters, and other filesystem-hostile characters.

## Input routing

Route the workflow from the user's input before doing any heavy work.

1. If the user gave a URL:
   - probe metadata first
   - if the selected URL may hide the surrounding series container, also probe the canonical container URL before resolving the project root
   - resolve the project root from that metadata
   - if the metadata contains multiple entries, choose the intended item before resolving the root
   - probe subtitle availability before deciding whether transcription is needed
2. If the user gave a local video file:
   - skip all download steps
   - resolve the project root from the local file path and any reliable series title the user provided
   - check for local sidecar subtitle files with `subskills/media-transcribe/scripts/find_local_subtitles.py`
3. Use the best available subtitle or transcript source in this order:
   - downloaded regular subtitle tracks
   - local sidecar subtitle files for a local video
   - local SRT produced by `media-transcribe`
   - danmaku only as last-resort context, never as a substitute for spoken-content transcription

## Default project layout

After choosing the project root, keep everything for that video inside it.

If this is a standalone video:

- `<workspace_root>/output/<Video Title>/video/`
- `<workspace_root>/output/<Video Title>/audio/`
- `<workspace_root>/output/<Video Title>/subtitles/`
- `<workspace_root>/output/<Video Title>/transcripts/`
- `<workspace_root>/output/<Video Title>/keyframes/`
- `<workspace_root>/output/<Video Title>/notes.md`
- `<workspace_root>/output/<Video Title>/keyframe_timestamps.txt`

If this video belongs to a series, add one more level first:

- `<workspace_root>/output/<Series Title>/<Video Title>/video/`
- `<workspace_root>/output/<Series Title>/<Video Title>/audio/`
- `<workspace_root>/output/<Series Title>/<Video Title>/subtitles/`
- `<workspace_root>/output/<Series Title>/<Video Title>/transcripts/`
- `<workspace_root>/output/<Series Title>/<Video Title>/keyframes/`
- `<workspace_root>/output/<Series Title>/<Video Title>/notes.md`
- `<workspace_root>/output/<Series Title>/<Video Title>/keyframe_timestamps.txt`

The user explicitly wants all screenshots under the chosen project root's `keyframes/` directory.

## Workflow

1. Determine whether the input is a URL or a local video path.
2. If the input is a URL, dump metadata first and resolve the project root with `subskills/yt-dlp/scripts/resolve_project_root.py` before any download step.
3. If the selected URL points at one entry inside a larger series and hides the container metadata, probe the canonical series/container URL first, then select the intended item with `--entry-index` or explicit titles.
4. If that metadata is a multi-entry container, choose the specific item first and pass `--entry-index` or `--video-title` to `resolve_project_root.py`.
5. If the input is a local video path, resolve the project root with `subskills/yt-dlp/scripts/resolve_project_root.py` from the local file path and skip download steps entirely.
6. Create `video/`, `audio/`, `subtitles/`, `transcripts/`, and `keyframes/` inside that project root.
7. For a URL source, probe the subtitle situation with the `yt-dlp` subskill. If the site may require login, make subtitle probes with the same cookies strategy used for subtitle downloads.
8. For a local video source, probe sibling subtitle files and common subtitle subdirectories with `subskills/media-transcribe/scripts/find_local_subtitles.py`.
9. Only download the video when the input is a URL, and save it to `<project_root>/video/`.
10. If the URL source has usable subtitle tracks, download them to `<project_root>/subtitles/` and use them as the primary text source.
11. If the local video source has usable sidecar subtitle files, copy or reuse them under `<project_root>/subtitles/` and use them as the primary text source.
12. Only if no usable subtitle text source exists, create or reuse audio under `<project_root>/audio/` and invoke the `media-transcribe` subskill to create an SRT transcript under `<project_root>/transcripts/`.
    - if the input is a local or downloaded video file, use `scripts/prepare_audio.py` so the audio artifact lives deterministically under `<project_root>/audio/`
    - if the input is already a local audio file, copy it into `<project_root>/audio/` or point `prepare_audio.py` at it so the note project stays self-contained
13. Extract scene-change keyframes with `scripts/extract_keyframes.py` into `<project_root>/keyframes/`.
14. Read the chosen subtitle/transcript and identify important timestamps such as:
    - section transitions
    - slides with definitions or equations
    - code or demo milestones
    - diagrams, tables, and architecture overviews
15. Save the chosen timestamps to `<project_root>/keyframe_timestamps.txt`, one timestamp per line, then run `scripts/extract_keyframes.py` again with `--timestamps-file`.
16. The script only extracts candidate images. The model must review those candidates and keep only the most informative screenshots.
17. Write `<project_root>/notes.md` by filling `assets/note-template.md` as the primary structure. Only diverge when the video clearly requires it.

## Keyframe extraction

The helper script only extracts candidate frames. It does not score, rank, deduplicate, or select them for you. It does clear stale `scene-*.jpg` and `cue-*.jpg` candidates before rewriting those sets, so reruns stay deterministic.

Use the bundled helper script:

```bash
cd .agent/skills/video-study-notes
.venv/bin/python scripts/extract_keyframes.py --video "<project_root>/video/example.mp4" --output-dir "<project_root>/keyframes"
```

After you decide which subtitle/transcript timestamps are important, place them in a text file such as `<project_root>/keyframe_timestamps.txt`:

```text
12.5
85.0
00:03:41.200
```

Then extract those exact frames:

```bash
cd .agent/skills/video-study-notes
.venv/bin/python scripts/extract_keyframes.py --video "<project_root>/video/example.mp4" --output-dir "<project_root>/keyframes" --timestamps-file "<project_root>/keyframe_timestamps.txt" --no-scene-detect
```

## Selection rules

The model, not the script, is responsible for reviewing the extracted images and deciding which ones to keep in the final note.

Prefer screenshots that carry information density, not just visual variety.

Keep:

- slides with equations, diagrams, architecture drawings, tables, code, or summary bullets
- screens that clearly mark a section change
- demo states that show a meaningful before/after or a key result

Avoid:

- blank or transition frames
- repeated talking-head shots
- near-duplicate slides
- frames where text is unreadable

As a default, keep roughly 1 to 3 images per major section.

## Notes writing rules

- Use `assets/note-template.md` as the primary note structure.
- Write the final note in Chinese by default.
- Keep important technical terms, API names, commands, model names, and acronyms in their original English form when that improves precision.
- Fill the template sections instead of inventing a brand new outline.
- In the template's "内容详解" section, prefer time-anchored segments or clearly separated topic blocks.
- Insert each selected image immediately after the paragraph or bullets it supports.
- Use relative Markdown image paths such as `![Diagram](keyframes/scene-0007.jpg)`.
- Do not leave hard-coded placeholder image links in the final note. Every referenced image path must exist.
- If the video contains code or formulas, explicitly call out the important symbols, assumptions, and pitfalls.
- End with a short `Takeaways` section, matching the template.

## Output contract

Always produce:

- one dedicated project root per video: `<workspace_root>/output/<Video Title>/` or `<workspace_root>/output/<Series Title>/<Video Title>/`
- downloaded media nested inside that project root, never flattened into the top-level `output/`
- screenshots under `<project_root>/keyframes/`
- one final note at `<project_root>/notes.md`

If the video is part of a series / playlist / course, never skip the extra series-level folder.

## Cleanup

- Treat probe-time metadata dumps, ad hoc contact sheets, and other scratch files outside `<project_root>/` as temporary working state.
- After the final note and kept assets have been written and verified, remove one-off temporary files and directories that are not part of the output contract.
- Inside `<project_root>/keyframes/`, keep the screenshots referenced by `notes.md` and remove unselected candidate frames unless the user explicitly asked to keep the full candidate set.

## Final checklist

- The project root was chosen after checking whether the video belongs to a series.
- The video is downloaded into the per-video folder only when the input source is a URL.
- The best available subtitle or transcript exists inside that per-video folder, and transcription was used only when no usable subtitle text source existed.
- Candidate frames were extracted into that per-video folder.
- `notes.md` only references image files that actually exist.
- Uninformative frames that were not selected for the note were discarded unless the user asked to keep all candidates.
- `<project_root>/notes.md` follows `assets/note-template.md` unless there is a clear reason to diverge.
- Temporary probe files created outside `<project_root>/` were cleaned up before finishing.
