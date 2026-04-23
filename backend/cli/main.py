"""CodeWatch CLI — one-shot review for pre-commit / CI use.

Talks directly to Ollama. Does not require the FastAPI server to be running.
Exit codes are designed for CI gating:

    0  no critical issues
    1  review completed, critical issues found
    2  reviewer could not run (ollama down, file missing, etc.)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger("codewatch.cli")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)


async def _run_review(file_path: Path, fail_on: str, quiet: bool) -> int:
    from backend.core.config import get_config
    from backend.services.ollama_client import (
        OllamaModelNotFoundError,
        OllamaUnavailableError,
        get_ollama_client,
    )
    from backend.services.prompt_builder import build_prompt
    from backend.services.reviewer import _detect_severity
    from backend.utils.language import get_language

    cfg = get_config()
    if not cfg.model:
        print("ERROR: no model configured. Set `model:` in config.yaml.", file=sys.stderr)
        return 2

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"ERROR: cannot read {file_path}: {exc}", file=sys.stderr)
        return 2

    language = get_language(str(file_path))
    prompt = build_prompt(
        filename=file_path.name,
        language=language,
        mode="full",
        payload=content,
        max_chars=cfg.prompt_max_chars,
    )

    client = get_ollama_client()
    full_text = ""
    try:
        async for token in client.generate_stream(cfg.model, prompt):
            full_text += token
            if not quiet:
                sys.stdout.write(token)
                sys.stdout.flush()
    except OllamaUnavailableError as exc:
        print(f"\nERROR: Ollama unavailable: {exc}", file=sys.stderr)
        return 2
    except OllamaModelNotFoundError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        await client.close()

    if not quiet:
        sys.stdout.write("\n")

    severity = _detect_severity(full_text, cfg.min_confidence)
    rank = {"suggestion": 0, "warning": 1, "critical": 2}
    print(f"\n[codewatch] severity={severity} file={file_path}", file=sys.stderr)
    if rank.get(severity, 0) >= rank.get(fail_on, 2):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codewatch",
        description="Local AI code review. Run a one-shot review for pre-commit/CI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Review one or more files and exit non-zero on issues.")
    review.add_argument("paths", nargs="+", help="File(s) to review.")
    review.add_argument(
        "--fail-on",
        choices=("critical", "warning", "suggestion"),
        default="critical",
        help="Minimum severity that causes a non-zero exit (default: critical).",
    )
    review.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress streaming review output; only print final severity.",
    )
    review.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging on stderr."
    )

    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))

    if args.command != "review":
        parser.error(f"unknown command {args.command!r}")
        return 2  # unreachable

    worst = 0
    for raw in args.paths:
        path = Path(raw)
        if not path.is_file():
            print(f"ERROR: not a file: {raw}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        code = asyncio.run(_run_review(path, args.fail_on, args.quiet))
        worst = max(worst, code)
    return worst


if __name__ == "__main__":
    sys.exit(main())
