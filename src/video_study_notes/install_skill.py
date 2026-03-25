from __future__ import annotations

import argparse
from contextlib import ExitStack
from importlib.resources import as_file, files
import shutil
import sys
from pathlib import Path


DEFAULT_SKILL_NAME = "video-study-notes"
DEFAULT_SKILLS_DIR = ".agents/skills"

# Keep this map aligned with spec-kit AGENT_CONFIG folders.
AGENT_CONFIG = {
    "copilot": {"folder": ".github/"},
    "claude": {"folder": ".claude/"},
    "gemini": {"folder": ".gemini/"},
    "cursor-agent": {"folder": ".cursor/"},
    "qwen": {"folder": ".qwen/"},
    "opencode": {"folder": ".opencode/"},
    "codex": {"folder": ".agents/"},
    "windsurf": {"folder": ".windsurf/"},
    "junie": {"folder": ".junie/"},
    "kilocode": {"folder": ".kilocode/"},
    "auggie": {"folder": ".augment/"},
    "codebuddy": {"folder": ".codebuddy/"},
    "qodercli": {"folder": ".qoder/"},
    "roo": {"folder": ".roo/"},
    "kiro-cli": {"folder": ".kiro/"},
    "amp": {"folder": ".agents/"},
    "shai": {"folder": ".shai/"},
    "tabnine": {"folder": ".tabnine/agent/"},
    "agy": {"folder": ".agent/"},
    "bob": {"folder": ".bob/"},
    "vibe": {"folder": ".vibe/"},
    "kimi": {"folder": ".kimi/"},
    "trae": {"folder": ".trae/"},
    "pi": {"folder": ".pi/"},
    "iflow": {"folder": ".iflow/"},
    "generic": {"folder": None},
}

AI_ASSISTANT_ALIASES = {
    "kiro": "kiro-cli",
}

AGENT_SKILLS_DIR_OVERRIDES = {
    "codex": ".agents/skills",
}

AGENT_DIR_IGNORE_PATTERNS = (
    ".agents",
    ".agent",
    ".claude",
    ".gemini",
    ".github",
    ".cursor",
    ".qwen",
    ".opencode",
    ".windsurf",
    ".junie",
    ".kilocode",
    ".augment",
    ".codebuddy",
    ".qoder",
    ".roo",
    ".kiro",
    ".shai",
    ".tabnine",
    ".bob",
    ".vibe",
    ".kimi",
    ".trae",
    ".pi",
    ".iflow",
)


def _build_ai_assistant_help() -> str:
    non_generic_agents = sorted(agent for agent in AGENT_CONFIG if agent != "generic")
    base_help = (
        f"AI assistant to use: {', '.join(non_generic_agents)}, "
        "or generic (requires --ai-commands-dir)."
    )
    if not AI_ASSISTANT_ALIASES:
        return base_help

    alias_phrases: list[str] = []
    for alias, target in sorted(AI_ASSISTANT_ALIASES.items()):
        alias_phrases.append(f"'{alias}' as an alias for '{target}'")

    if len(alias_phrases) == 1:
        aliases_text = alias_phrases[0]
    else:
        aliases_text = ", ".join(alias_phrases[:-1]) + " and " + alias_phrases[-1]
    return base_help + " Use " + aliases_text + "."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-notes install-skill",
        description="Install this skill into an AI client's local skills directory.",
    )
    parser.add_argument(
        "--ai",
        default="codex",
        help=_build_ai_assistant_help(),
    )
    parser.add_argument(
        "--ai-commands-dir",
        default=None,
        help="Directory for agent command files (required with --ai generic).",
    )
    parser.add_argument(
        "--project",
        default=".",
        help="Target project root where AI skills directory should be resolved.",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Path to the local skill folder (must contain SKILL.md). Defaults to auto-detect.",
    )
    parser.add_argument(
        "--name",
        default=DEFAULT_SKILL_NAME,
        help=f"Installed skill directory name (default: {DEFAULT_SKILL_NAME}).",
    )
    parser.add_argument(
        "--mode",
        choices=["symlink", "copy"],
        default="symlink",
        help="Install as symlink (preferred) or copy.",
    )
    parser.add_argument(
        "--target-base",
        default=None,
        help="Override resolved skills directory. If set, --project and --ai mapping are ignored.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing target path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without modifying filesystem.",
    )
    return parser


def _normalize_ai(ai: str) -> str:
    return AI_ASSISTANT_ALIASES.get(ai, ai)


def _resolve_target_base(ai: str, project: Path, ai_commands_dir: str | None) -> Path:
    if ai not in AGENT_CONFIG:
        supported = ", ".join(sorted(AGENT_CONFIG.keys()))
        raise ValueError(
            f"Invalid value for --ai: '{ai}'.\n"
            f"Supported values: {supported}.\n"
            "Run `video-notes install-skill --help` to see examples."
        )

    if ai == "generic":
        if not ai_commands_dir:
            raise ValueError(
                "--ai-commands-dir is required when using --ai generic.\n"
                "Example: video-notes install-skill --ai generic "
                "--ai-commands-dir .myagent/commands --project /path/to/project"
            )
        return (project / ai_commands_dir).resolve()

    if ai_commands_dir:
        raise ValueError(
            f"--ai-commands-dir can only be used with --ai generic (not '{ai}').\n"
            f"Try removing --ai-commands-dir, or switch to --ai generic."
        )

    if ai in AGENT_SKILLS_DIR_OVERRIDES:
        return (project / AGENT_SKILLS_DIR_OVERRIDES[ai]).resolve()

    agent_folder = AGENT_CONFIG[ai].get("folder")
    if agent_folder:
        return (project / Path(agent_folder.rstrip("/")) / "skills").resolve()

    return (project / DEFAULT_SKILLS_DIR).resolve()


def _find_source_from_module() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "SKILL.md").is_file():
            return parent
    return None


def _resolve_source(raw: str | None) -> Path:
    candidates: list[Path] = []

    if raw:
        candidates.append(Path(raw).expanduser())

    cwd = Path.cwd()
    candidates.append(cwd)

    from_module = _find_source_from_module()
    if from_module:
        candidates.append(from_module)

    for candidate in candidates:
        path = candidate.resolve()
        if (path / "SKILL.md").is_file():
            return path

    raise FileNotFoundError(
        "Could not find a skill source directory containing SKILL.md.\n"
        "How to fix:\n"
        "1) Run this command in your skill repository root, or\n"
        "2) Pass --source <path-to-skill-dir> explicitly."
    )


def _resolve_source_with_packaged_fallback(raw: str | None, stack: ExitStack) -> Path:
    if raw:
        explicit = Path(raw).expanduser().resolve()
        if (explicit / "SKILL.md").is_file():
            return explicit
        raise FileNotFoundError(
            f"Invalid --source: {explicit}\n"
            "Expected a directory that contains SKILL.md."
        )

    try:
        return _resolve_source(raw)
    except FileNotFoundError:
        pass

    try:
        packaged = files("video_study_notes") / "skill_template"
        packaged_path = stack.enter_context(as_file(packaged))
    except Exception as exc:
        raise FileNotFoundError(
            "Could not resolve skill source from local path or packaged template.\n"
            "Pass --source <path-to-skill-dir> explicitly."
        ) from exc

    packaged_skill = packaged_path / "SKILL.md"
    if packaged_skill.is_file():
        return packaged_path

    raise FileNotFoundError(
        "Packaged skill template is missing SKILL.md.\n"
        "Pass --source <path-to-skill-dir> explicitly."
    )


def _is_target_under_copy_ignored_dir(source: Path, target: Path) -> bool:
    try:
        rel = target.resolve().relative_to(source.resolve())
    except ValueError:
        return False

    if not rel.parts:
        return False
    return rel.parts[0] in AGENT_DIR_IGNORE_PATTERNS


def _resolve_effective_mode(
    source: Path, target: Path, requested_mode: str
) -> tuple[str, str | None]:
    if not _paths_overlap(source, target):
        return requested_mode, None

    if not _is_target_under_copy_ignored_dir(source, target):
        raise ValueError(
            "Source and target paths overlap in an unsafe location.\n"
            f"Source: {source}\n"
            f"Target: {target}\n"
            "Use one of these fixes:\n"
            "1) Set --project to another directory, or\n"
            "2) Set --target-base to a directory outside the source skill folder."
        )

    if requested_mode == "symlink":
        return "copy", "Source and target overlap; switched mode from symlink to copy."

    return requested_mode, None


def _remove_existing(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _copy_tree(source: Path, target: Path) -> None:
    ignore = shutil.ignore_patterns(
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "*.pyc",
        ".tmp-skills",
        "*tmp-skills*",
        "TMP-SK~1",
        ".empty-tmp",
        "*empty-tmp*",
        *AGENT_DIR_IGNORE_PATTERNS,
    )
    shutil.copytree(source, target, ignore=ignore)


def _install_symlink_or_copy(source: Path, target: Path, mode: str) -> tuple[str, str]:
    if mode == "copy":
        _copy_tree(source, target)
        return "copied", ""

    try:
        target.symlink_to(source, target_is_directory=True)
        return "symlinked", ""
    except OSError as exc:
        _copy_tree(source, target)
        return "copied", f"Symlink failed ({exc}); fell back to copy."


def _paths_overlap(left: Path, right: Path) -> bool:
    left_resolved = left.resolve()
    right_resolved = right.resolve()
    return (
        left_resolved == right_resolved
        or left_resolved in right_resolved.parents
        or right_resolved in left_resolved.parents
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    selected_ai = _normalize_ai(args.ai)

    with ExitStack() as stack:
        try:
            source = _resolve_source_with_packaged_fallback(args.source, stack)
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        project_path = Path(args.project).expanduser().resolve()
        try:
            if args.target_base:
                target_base = Path(args.target_base).expanduser().resolve()
            else:
                target_base = _resolve_target_base(
                    selected_ai, project_path, args.ai_commands_dir
                )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        target = target_base / args.name

        try:
            effective_mode, mode_note = _resolve_effective_mode(
                source, target, args.mode
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        if args.dry_run:
            print(f"AI: {selected_ai}")
            print(f"Project: {project_path}")
            print(f"Mode: {effective_mode}")
            print(f"Source: {source}")
            print(f"Target: {target}")
            if mode_note:
                print(mode_note)
            print("Dry run complete. No changes were made.")
            return 0

        target_base.mkdir(parents=True, exist_ok=True)

        if target.exists() or target.is_symlink():
            if not args.force:
                print(
                    f"Target already exists: {target}\n"
                    "Use --force to overwrite.\n"
                    "Or choose a different --name / --project / --target-base.",
                    file=sys.stderr,
                )
                return 1
            _remove_existing(target)

        action, fallback_note = _install_symlink_or_copy(source, target, effective_mode)
        print(f"{action.capitalize()} skill to: {target}")
        if mode_note:
            print(mode_note)
        if fallback_note:
            print(fallback_note)
        print("Restart your AI session so the new skill can be discovered.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
