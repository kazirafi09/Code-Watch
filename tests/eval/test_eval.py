"""End-to-end prompt-quality eval against a live Ollama.

Run with ``pytest -m eval``. Skipped by default because it requires:

* an Ollama daemon reachable at ``OLLAMA_URL`` (default http://localhost:11434)
* a pulled code model (``OLLAMA_MODEL``, default ``qwen2.5-coder:7b``)

Metrics computed across the whole corpus:

* **Recall**  = critical-flagged buggy fixtures / total buggy fixtures
* **Precision** = critical-flagged buggy fixtures /
  (critical-flagged buggy + critical-flagged clean)

Thresholds come from AUDIT.md §6.1 Week 2: precision ≥ 0.7, recall ≥ 0.6 on
criticals. Tune ``OLLAMA_MODEL`` to see how the same prompt fares against
different local models.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import httpx
import pytest

from backend.services.ollama_client import (
    OllamaClient,
    OllamaModelNotFoundError,
    OllamaUnavailableError,
)
from backend.services.prompt_builder import build_prompt
from backend.services.review_parser import filter_by_confidence, parse_issues
from tests.eval._fixtures import ALL_FIXTURES, BUGGY, CLEAN, Fixture, ensure_fixtures

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
MIN_CONFIDENCE = float(os.environ.get("EVAL_MIN_CONFIDENCE", "0.5"))
MIN_PRECISION = float(os.environ.get("EVAL_MIN_PRECISION", "0.7"))
MIN_RECALL = float(os.environ.get("EVAL_MIN_RECALL", "0.6"))


pytestmark = pytest.mark.eval


def _ollama_reachable() -> bool:
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


if not _ollama_reachable():
    pytest.skip(
        f"Ollama not reachable at {OLLAMA_URL}; set OLLAMA_URL/OLLAMA_MODEL to run the eval.",
        allow_module_level=True,
    )


@dataclass
class Outcome:
    fixture: Fixture
    flagged_critical: bool
    raw_text: str


async def _run_one(client: OllamaClient, fx: Fixture) -> Outcome:
    prompt = build_prompt(
        filename=fx.relpath.rsplit("/", 1)[-1],
        language=fx.language,
        mode="full",
        payload=fx.content,
        max_chars=16000,
    )
    chunks: list[str] = []
    async for tok in client.generate_stream(OLLAMA_MODEL, prompt):
        chunks.append(tok)
    text = "".join(chunks)
    issues = filter_by_confidence(parse_issues(text), MIN_CONFIDENCE)
    flagged = any(i.severity == "critical" for i in issues)
    return Outcome(fixture=fx, flagged_critical=flagged, raw_text=text)


async def _run_all() -> list[Outcome]:
    ensure_fixtures()
    client = OllamaClient(OLLAMA_URL, timeout=180)
    outcomes: list[Outcome] = []
    # Sequential to match runtime behavior (max_concurrency=1) and to avoid
    # thrashing the local GPU.
    for fx in ALL_FIXTURES:
        try:
            outcomes.append(await _run_one(client, fx))
        except OllamaModelNotFoundError:
            pytest.skip(f"Model '{OLLAMA_MODEL}' not pulled")
        except OllamaUnavailableError as exc:
            pytest.skip(f"Ollama became unavailable mid-run: {exc}")
    return outcomes


def test_precision_recall_on_critical():
    outcomes = asyncio.run(_run_all())
    by_relpath = {o.fixture.relpath: o for o in outcomes}

    tp = sum(1 for fx in BUGGY if by_relpath[fx.relpath].flagged_critical)
    fn_list = [fx.relpath for fx in BUGGY if not by_relpath[fx.relpath].flagged_critical]
    fp_list = [fx.relpath for fx in CLEAN if by_relpath[fx.relpath].flagged_critical]
    fp = len(fp_list)

    recall = tp / max(len(BUGGY), 1)
    precision = tp / max(tp + fp, 1)

    report = (
        f"\nEval model: {OLLAMA_MODEL}  threshold: {MIN_CONFIDENCE}"
        f"\nRecall (critical):    {recall:.2f}  (target {MIN_RECALL:.2f})"
        f"  TP={tp}/{len(BUGGY)}"
        f"\nPrecision (critical): {precision:.2f}  (target {MIN_PRECISION:.2f})"
        f"  FP={fp}/{len(CLEAN)}"
        f"\nMissed buggy:   {fn_list}"
        f"\nFalse criticals on clean: {fp_list}\n"
    )
    print(report)

    assert recall >= MIN_RECALL, report
    assert precision >= MIN_PRECISION, report
