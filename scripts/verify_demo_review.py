"""E2E verification: run the real prompt pipeline against the demo-dogfooding file.

Matches the AUDIT.md §6.1 Week 2 scenario: SQL injection via f-string, hardcoded
API key, ``shell=True``, ``pickle.loads``. Asserts ``severity == critical`` and
that at least the SQLi and hardcoded-key issues are flagged at confidence >= 0.5.

Usage:

    .venv/Scripts/python.exe scripts/verify_demo_review.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Force stdout to UTF-8 so we can stream Markdown output (em-dash, arrows, etc.)
# that the model emits.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from backend.services.ollama_client import OllamaClient  # noqa: E402
from backend.services.prompt_builder import build_prompt  # noqa: E402
from backend.services.review_parser import filter_by_confidence, parse_issues  # noqa: E402
from backend.services.reviewer import _detect_severity  # noqa: E402

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")

DEMO_FILE = """\
import hashlib
import pickle
import subprocess

import sqlite3

API_KEY = "sk-proj-9f2e4a1b8c7d6e5f4a3b2c1d0e9f8a7b"


def find_user(name):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cur.fetchall()


def ping(host):
    subprocess.run(f"ping -c 1 {host}", shell=True)


def load_session(blob):
    return pickle.loads(blob)


def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()
"""


async def main() -> int:
    prompt = build_prompt(
        filename="demo.py",
        language="python",
        mode="full",
        payload=DEMO_FILE,
        max_chars=16000,
    )
    client = OllamaClient(OLLAMA_URL, timeout=180)
    chunks: list[str] = []
    print(f"-> streaming review from {OLLAMA_MODEL} ...", flush=True)
    async for tok in client.generate_stream(OLLAMA_MODEL, prompt):
        chunks.append(tok)
    text = "".join(chunks)
    print("\n--- model output ---\n" + text + "\n--- end ---\n")

    issues = parse_issues(text)
    surfaced = filter_by_confidence(issues, min_confidence=0.5)
    severity = _detect_severity(text, min_confidence=0.5)

    print(f"parsed {len(issues)} issue(s); {len(surfaced)} at confidence >= 0.5")
    for it in surfaced:
        print(f"  [{it.severity:10s}] conf={it.confidence:.2f}  L{it.line}  {it.title}")

    criticals = [i for i in surfaced if i.severity == "critical"]
    joined = " ".join(f"{i.title} {i.rationale}".lower() for i in criticals)

    flagged_sqli = any(k in joined for k in ("sql injection", "sql-injection", "f-string sql", "sqli"))
    flagged_key = any(k in joined for k in ("hardcoded", "api key", "api_key", "secret"))

    ok = True
    print(f"\nSeverity: {severity}  (expected: critical)")
    if severity != "critical":
        print("[FAIL] expected severity=critical")
        ok = False
    print(f"SQL injection flagged critical:     {flagged_sqli}")
    print(f"Hardcoded API key flagged critical: {flagged_key}")
    if not flagged_sqli:
        print("[FAIL] SQL injection not flagged at critical confidence")
        ok = False
    if not flagged_key:
        print("[FAIL] Hardcoded API key not flagged at critical confidence")
        ok = False

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
