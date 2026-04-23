"""Parse structured issues from the reviewer's free-form output.

The prompt asks the model for a trailing ``## Machine-readable`` section with a
JSON block describing each issue. We also fall back to parsing the inline
``### [severity] L<n> — ... (confidence: X.YZ)`` headers in case the JSON is
missing or malformed.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(
    r"##\s*Machine-readable\s*\n+```(?:json)?\s*(\{.*?\})\s*```",
    re.IGNORECASE | re.DOTALL,
)
_ANY_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{(?:[^`]|`(?!``))*?\"issues\"\s*:[^`]*?\})\s*```",
    re.DOTALL,
)
_HEADER_RE = re.compile(
    r"###\s*\[(?P<severity>critical|warning|suggestion)\]\s*"
    r"(?:L(?P<line>\d+)\s*[—\-:]\s*)?"
    r"(?P<title>[^\n]*?)"
    r"(?:\(confidence[:=]?\s*(?P<confidence>\d*\.?\d+)\s*\))?"
    r"\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_SEVERITY_RANK = {"critical": 3, "warning": 2, "suggestion": 1}


@dataclass
class Issue:
    severity: str
    confidence: float
    line: int | None = None
    title: str = ""
    rationale: str = ""


def _coerce_issue(raw: dict) -> Issue | None:
    sev = str(raw.get("severity", "")).strip().lower()
    if sev not in _SEVERITY_RANK:
        return None
    try:
        conf = float(raw.get("confidence", 0.5))
    except (TypeError, ValueError):
        conf = 0.5
    conf = max(0.0, min(1.0, conf))
    line_raw = raw.get("line")
    line: int | None
    try:
        line = int(line_raw) if line_raw not in (None, "", "null") else None
    except (TypeError, ValueError):
        line = None
    return Issue(
        severity=sev,
        confidence=conf,
        line=line,
        title=str(raw.get("title", "")).strip(),
        rationale=str(raw.get("rationale", "")).strip(),
    )


def _parse_json_block(text: str) -> list[Issue] | None:
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        match = _ANY_JSON_FENCE_RE.search(text)
    if not match:
        return None
    raw = match.group(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("Malformed JSON block in review output")
        return None
    issues_raw = data.get("issues") if isinstance(data, dict) else None
    if not isinstance(issues_raw, list):
        return None
    issues = [it for it in (_coerce_issue(r) for r in issues_raw if isinstance(r, dict)) if it]
    return issues


def _parse_headers(text: str) -> list[Issue]:
    # Only scan inside the "## Issues" section if present, to avoid picking up
    # examples from the prompt preamble echoed by the model.
    sections = re.split(r"(?im)^##\s+issues\s*$", text, maxsplit=1)
    body = sections[1] if len(sections) > 1 else text
    # Stop at the next "## " heading.
    body = re.split(r"(?m)^##\s+\S", body, maxsplit=1)[0]
    issues: list[Issue] = []
    for match in _HEADER_RE.finditer(body):
        sev = match.group("severity").lower()
        conf_raw = match.group("confidence")
        try:
            conf = float(conf_raw) if conf_raw else 0.7  # default for legacy output
        except ValueError:
            conf = 0.7
        conf = max(0.0, min(1.0, conf))
        line_raw = match.group("line")
        line = int(line_raw) if line_raw else None
        issues.append(
            Issue(
                severity=sev,
                confidence=conf,
                line=line,
                title=(match.group("title") or "").strip(),
            )
        )
    return issues


def parse_issues(text: str) -> list[Issue]:
    """Return the list of issues surfaced by the model.

    Prefers the JSON block; falls back to header parsing when JSON is missing
    or unparseable.
    """
    from_json = _parse_json_block(text)
    if from_json is not None:
        return from_json
    return _parse_headers(text)


def classify_severity(issues: list[Issue], min_confidence: float = 0.5) -> str:
    """Pick the highest severity among issues whose confidence >= threshold."""
    filtered = [i for i in issues if i.confidence >= min_confidence]
    if not filtered:
        return "suggestion"
    top = max(filtered, key=lambda i: _SEVERITY_RANK[i.severity])
    return top.severity


def filter_by_confidence(issues: list[Issue], min_confidence: float = 0.5) -> list[Issue]:
    return [i for i in issues if i.confidence >= min_confidence]
