#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes.util
import json
import os
import site
import shutil
import sys
import sysconfig
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[3]
SKILL_VENV_PYTHON = SKILL_ROOT / ".venv" / "bin" / "python"

if (
    SKILL_VENV_PYTHON.is_file()
    and Path(sys.executable) != SKILL_VENV_PYTHON
    and os.environ.get("VIDEO_NOTES_TRANSCRIBE_VENV_REEXEC") != "1"
):
    env = os.environ.copy()
    env["VIDEO_NOTES_TRANSCRIBE_VENV_REEXEC"] = "1"
    os.execve(
        str(SKILL_VENV_PYTHON),
        [str(SKILL_VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
        env,
    )


def _site_packages() -> list[Path]:
    candidates: list[Path] = []
    try:
        candidates.extend(Path(path) for path in site.getsitepackages())
    except Exception:
        pass

    for key in ("purelib", "platlib"):
        value = sysconfig.get_paths().get(key)
        if value:
            candidates.append(Path(value))

    try:
        candidates.append(Path(site.getusersitepackages()))
    except Exception:
        pass

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def _nvidia_library_dirs() -> list[Path]:
    candidates: list[Path] = []
    for site_packages in _site_packages():
        for relative in ("nvidia/cublas/lib", "nvidia/cudnn/lib"):
            candidate = site_packages / relative
            if candidate.exists():
                candidates.append(candidate)
    return candidates


def _prepend_linux_library_path() -> None:
    existing = [str(path) for path in _nvidia_library_dirs()]
    if not existing:
        return
    current = [entry for entry in os.environ.get("LD_LIBRARY_PATH", "").split(":") if entry]
    merged = existing + [entry for entry in current if entry not in existing]
    merged_value = ":".join(merged)
    if os.environ.get("LD_LIBRARY_PATH") == merged_value:
        return
    if os.environ.get("VIDEO_NOTES_TRANSCRIBE_LD_REEXEC") != "1":
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = merged_value
        env["VIDEO_NOTES_TRANSCRIBE_LD_REEXEC"] = "1"
        runner = sys.executable
        os.execve(runner, [runner, str(Path(__file__).resolve()), *sys.argv[1:]], env)
    os.environ["LD_LIBRARY_PATH"] = merged_value


if sys.platform.startswith("linux"):
    _prepend_linux_library_path()

from faster_whisper import BatchedInferencePipeline, WhisperModel


def srt_ts(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours = total_ms // 3_600_000
    total_ms %= 3_600_000
    minutes = total_ms // 60_000
    total_ms %= 60_000
    secs = total_ms // 1_000
    millis = total_ms % 1_000
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def choose_defaults() -> tuple[str, str, str, bool, int]:
    cublas_ready = bool(ctypes.util.find_library("cublas")) or any(
        any(path.glob("libcublas.so*")) for path in _nvidia_library_dirs()
    )
    if shutil.which("nvidia-smi") and cublas_ready:
        return ("turbo", "cuda", "float16", True, 16)
    return ("small", "cpu", "int8", False, 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe audio/video to txt and srt with faster-whisper.")
    parser.add_argument("--input", required=True, help="Path to the local audio/video file.")
    parser.add_argument(
        "--output-dir",
        default="downloads/media-transcribe/transcripts",
        help="Directory for transcription outputs.",
    )
    parser.add_argument("--language", default=None, help="Language code, e.g. zh or en. Omit to auto-detect.")
    parser.add_argument("--model", default="auto", help="Whisper model name. Use auto for pragmatic defaults.")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"], help="Inference device.")
    parser.add_argument("--compute-type", default="auto", help="CTranslate2 compute type. Use auto for pragmatic defaults.")
    parser.add_argument("--beam-size", type=int, default=5, help="Beam size for decoding.")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size when batched inference is enabled.")
    parser.add_argument("--vad-filter", action="store_true", default=True, help="Enable VAD filtering.")
    parser.add_argument("--no-vad-filter", dest="vad_filter", action="store_false", help="Disable VAD filtering.")
    return parser


def resolve_runtime(args: argparse.Namespace) -> tuple[str, str, str, bool, int]:
    auto_model, auto_device, auto_compute, auto_batched, auto_batch = choose_defaults()
    model = auto_model if args.model == "auto" else args.model
    device = auto_device if args.device == "auto" else args.device
    compute = auto_compute if args.compute_type == "auto" else args.compute_type
    batched = auto_batched if device == auto_device else device == "cuda"
    batch_size = auto_batch if args.batch_size == 16 and args.model == "auto" and args.device == "auto" else args.batch_size
    return model, device, compute, batched, batch_size


def make_model(model_name: str, device: str, compute_type: str) -> WhisperModel:
    return WhisperModel(model_name, device=device, compute_type=compute_type)


def transcribe(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model_name, device, compute_type, batched, batch_size = resolve_runtime(args)

    try:
        model = make_model(model_name, device, compute_type)
    except Exception as exc:
        if device != "cuda":
            raise
        print(f"CUDA path failed ({exc}). Falling back to CPU int8 small.", file=sys.stderr)
        model_name, device, compute_type, batched, batch_size = ("small", "cpu", "int8", False, 1)
        model = make_model(model_name, device, compute_type)

    transcriber = BatchedInferencePipeline(model=model) if batched else model

    kwargs = {
        "beam_size": args.beam_size,
        "language": args.language,
        "vad_filter": args.vad_filter,
    }
    if batched:
        kwargs["batch_size"] = batch_size

    try:
        segments, info = transcriber.transcribe(str(input_path), **kwargs)
        segments = list(segments)
    except Exception as exc:
        if device != "cuda":
            raise
        print(f"CUDA transcription failed ({exc}). Falling back to CPU int8 small.", file=sys.stderr)
        model_name, device, compute_type, batched, batch_size = ("small", "cpu", "int8", False, 1)
        model = make_model(model_name, device, compute_type)
        transcriber = model
        kwargs = {
            "beam_size": args.beam_size,
            "language": args.language,
            "vad_filter": args.vad_filter,
        }
        segments, info = transcriber.transcribe(str(input_path), **kwargs)
        segments = list(segments)

    stem = input_path.stem
    txt_path = output_dir / f"{stem}.txt"
    srt_path = output_dir / f"{stem}.srt"
    json_path = output_dir / f"{stem}.transcription.json"

    full_text = "\n".join(segment.text.strip() for segment in segments if segment.text.strip())
    txt_path.write_text(full_text + ("\n" if full_text else ""), encoding="utf-8")

    with srt_path.open("w", encoding="utf-8") as handle:
        for idx, segment in enumerate(segments, 1):
            text = segment.text.strip()
            if not text:
                continue
            handle.write(f"{idx}\n")
            handle.write(f"{srt_ts(segment.start)} --> {srt_ts(segment.end)}\n")
            handle.write(text + "\n\n")

    payload = {
        "input": str(input_path),
        "outputs": {
            "txt": str(txt_path),
            "srt": str(srt_path),
            "json": str(json_path),
        },
        "detected_language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "duration_after_vad": getattr(info, "duration_after_vad", None),
        "model": model_name,
        "device": device,
        "compute_type": compute_type,
        "batched": batched,
        "beam_size": args.beam_size,
        "vad_filter": args.vad_filter,
        "segments": [
            {
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            }
            for segment in segments
        ],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Detected language: {info.language} ({info.language_probability:.4f})")
    print(f"TXT: {txt_path}")
    print(f"SRT: {srt_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(transcribe(build_parser().parse_args()))
