---
name: media-transcribe
description: Use this skill whenever a local audio or video file needs transcription, especially when an upstream source has no usable subtitle track. Also use it when the user asks to transcribe media that already exists locally or was downloaded by another workflow.
compatibility:
  tools: ["functions.exec_command"]
  dependencies: ["uv", ".venv/bin/python", "faster-whisper"]
---

# media-transcribe

This subskill is part of the self-contained `video-study-notes` skill. Its helper scripts live under `subskills/media-transcribe/scripts/`.

Use this companion skill when a local audio or video file needs transcription, especially when neither an upstream download nor a local sidecar subtitle file provides usable subtitle text.

Prefer the bundled Python script `subskills/media-transcribe/scripts/transcribe_audio.py`. Run it from the skill-local `.venv` managed by `uv`. If the input is a video file and the parent workflow wants a deterministic copy under `<project_root>/audio/`, first use `scripts/prepare_audio.py`.

## When to use

- an upstream probe reports no regular subtitle tracks
- a local video has no usable sidecar subtitle text file
- the source only exposes danmaku/xml and the user wants spoken-content transcription
- the user already has a downloaded audio/video file and wants text or subtitles

## Default approach

1. Prefer a local audio file as input. If the caller only has a local video file, first create `<project_root>/audio/<stem>.wav` (or another explicit format) with `scripts/prepare_audio.py`.
2. If the user only gave a URL, the caller can use a download-oriented skill first and then pass the local media file here.
3. Before invoking transcription, confirm that no usable subtitle text source already exists.
4. Use `subskills/media-transcribe/scripts/transcribe_audio.py` to create `.txt`, `.srt`, and `.json` outputs.
5. If the spoken language is obvious, pass it explicitly. For Chinese content, use `--language zh`.
6. Save outputs under the caller-provided `transcripts/` directory when the parent workflow already chose a per-video project root. Otherwise fall back to `downloads/media-transcribe/transcripts/`.

## Model strategy

- On a CUDA-capable machine, prefer model `turbo`, device `cuda`, compute type `float16`, and batched inference.
- On CPU-only machines, prefer model `small`, device `cpu`, compute type `int8`.
- If CUDA initialization fails, fall back to CPU automatically.

This is a pragmatic default: it favors high throughput on GPU while keeping CPU fallback usable.

## Commands

The examples below assume the current directory is the skill root.

Prepare audio deterministically from a local video before transcription:

```bash
mkdir -p output/example/audio
.venv/bin/python scripts/prepare_audio.py --input "output/example/video/example.mp4" --output-dir output/example/audio
```

Transcribe a local audio file with automatic device/model selection:

```bash
mkdir -p downloads/media-transcribe/transcripts
.venv/bin/python subskills/media-transcribe/scripts/transcribe_audio.py --input "downloads/media-transcribe/audio/example.m4a" --output-dir downloads/media-transcribe/transcripts --language zh
```

Force CPU mode:

```bash
.venv/bin/python subskills/media-transcribe/scripts/transcribe_audio.py --input "downloads/media-transcribe/audio/example.m4a" --device cpu --compute-type int8 --model small
```

## Output files

For an input named `example.m4a`, the script writes:

- `example.txt`
- `example.srt`
- `example.transcription.json`

## Notes

- Prefer existing subtitle text over transcription; prefer transcription over danmaku when the user wants actual spoken content.
- Keep the raw audio file; do not delete it after transcription.
- Report the output paths and detected language back to the user.
