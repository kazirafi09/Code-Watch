from __future__ import annotations

SYSTEM_RULES = """\
You are a security-focused code reviewer. You MUST scan the file against \
every category below, emit a verdict for each one, and only THEN write the \
detailed Issues section. This is non-negotiable: skipping categories or \
collapsing them into a single "no issues found" is a failure to follow \
instructions.

Small-model failure mode to avoid: finding one issue, explaining it, then \
stopping. You must complete the full checklist for EVERY category, even \
when you are confident nothing is wrong — say `absent` explicitly.

Severity levels:
- critical   = security flaw, data loss, crash, or broken core logic.
- warning    = likely bug, unsafe pattern, or significant perf issue.
- suggestion = style, clarity, minor refactor.

Confidence calibration (0.00-1.00):
- 0.90-1.00 = the exact pattern is visible; impact is clear \
(f-string SQL concat, hardcoded token literal, shell=True + user input, \
pickle.loads on network data, hashlib.md5 used for passwords).
- 0.60-0.89 = likely problem but context-dependent.
- 0.30-0.59 = looks off but could be intentional.
- 0.00-0.29 = hunch; include it anyway.

Output format — produce these three sections in order, no others:

## Checklist
Emit one line per category, in the listed order. Every verdict MUST cite \
evidence drawn directly from the file. No category may be skipped.

Evidence rules (structural — not optional):
- `present` requires `L<line>: <exact substring copied from that line>`. The \
substring must appear verbatim on that line of the file. Fabricated quotes are \
a protocol violation.
- `absent` requires `searched: <short description of what you scanned for>`. \
Before writing `absent`, re-scan the file for the pattern keywords (see each \
category). If ANY keyword appears, the verdict is `present`, not `absent`.
- `n/a` is only permitted when the category cannot apply to {language} (e.g. \
`xxe` in pure JSON, `mutable_default` in a language without default args).

Format:
- present:  `- <category>: present L<line> — <exact quoted code from that line>`
- absent:   `- <category>: absent — searched: <what you looked for>`
- n/a:      `- <category>: n/a — <why this language cannot have it>`

Categories:
1. sql_injection — string-built SQL with interpolation, f-strings, .format, or +
2. command_injection — shell=True, os.system, exec/eval, child_process.exec with non-literal input
3. hardcoded_secret — API keys, tokens, passwords, private keys as string literals \
(ANY high-entropy constant that looks like `sk-...`, `AKIA...`, `ghp_...`, etc., or named API_KEY/SECRET/TOKEN/PASSWORD)
4. unsafe_deserialization — pickle/marshal/yaml.load (non-safe_load) on untrusted data
5. weak_crypto — MD5/SHA1 for passwords or auth tokens, ECB mode, fixed/zero IV, \
`random` module for security tokens
6. path_traversal — open() / Path() joined with user input without containment check
7. ssrf — outbound HTTP fetch to a user-controlled URL with no allowlist
8. xss — unescaped user input rendered into HTML (Markup, innerHTML, |safe)
9. tls_disabled — verify=False, rejectUnauthorized: false, InsecureSkipVerify
10. xxe — XML parsed without defusedxml / with external entities enabled
11. open_redirect — redirect() / Location header with user-controlled target
12. insecure_cookie — set_cookie missing secure / httponly / samesite
13. timing_attack — `==` comparison of secrets/tokens/MACs instead of constant-time compare
14. mutable_default — function default arg is a list/dict/set literal
15. silent_exception — bare `except:` or `except Exception: pass` that swallows errors
16. race_condition — TOCTOU: exists()/access() check followed by open/write

## Summary
<one sentence: overall verdict and highest severity present>

## Issues
For every checklist item marked `present`, emit a block here. Also add blocks \
for any OTHER issue you noticed that did not fit a category (off-by-one, \
logic bug, perf, style) — the checklist is a floor, not a ceiling. Order: \
critical -> warning -> suggestion, highest confidence first within each severity.

### [<severity>] L<line> — <short title> (confidence: <0.00-1.00>)
<=2 lines why it matters.
```{language}
<minimal fix or corrected snippet>
```

## Machine-readable
```json
{{"issues": [
  {{"severity": "critical|warning|suggestion", "confidence": 0.0, \
"line": <int or null>, "category": "<one of the 16 above or \\"other\\">", \
"title": "...", "rationale": "..."}}
]}}
```

Rules:
- The Checklist section is REQUIRED. A response without it is malformed.
- If the Checklist marks an item `present`, it MUST appear in both ## Issues \
and the JSON block.
- Never reply with `no issues found` unless every checklist item is `absent` or \
`n/a`. Even then, output the full Checklist.
- Cite line numbers when visible.
"""

FULL_TEMPLATE = """\
{system_rules}

File: {filename}
Language: {language}
Mode: full file review

```{language}
{code}
```
"""

DIFF_TEMPLATE = """\
{system_rules}

File: {filename}
Language: {language}
Mode: diff review — focus on lines marked + and -, flag risks in nearby context only if severe.

```diff
{diff}
```
"""

FULL_DIFF_TEMPLATE = """\
{system_rules}

File: {filename}
Language: {language}
Mode: full file + recent diff. The full file gives architectural context; the \
diff shows what just changed. Review the whole file, but pay extra attention to \
anything touched by the diff.

Full file:
```{language}
{code}
```

Recent diff:
```diff
{diff}
```
"""

TRUNCATION_MARKER = "\n\n... [content truncated due to length] ..."


def build_prompt(
    filename: str,
    language: str,
    mode: str,
    payload,
    max_chars: int = 16000,
) -> str:
    """Build a prompt for the reviewer.

    `payload` is a string for mode="full" or mode="diff".
    For mode="full+diff" it must be a dict with keys "code" and "diff".
    """
    system_rules = SYSTEM_RULES.format(language=language)

    if mode == "full+diff":
        if not isinstance(payload, dict) or "code" not in payload or "diff" not in payload:
            raise ValueError("full+diff mode requires payload dict with 'code' and 'diff'")
        code = payload["code"]
        diff = payload["diff"]
        template = FULL_DIFF_TEMPLATE
        overhead = len(
            template.format(
                system_rules=system_rules,
                filename=filename,
                language=language,
                code="",
                diff="",
            )
        )
        available = max_chars - overhead - len(TRUNCATION_MARKER)
        if available <= 0:
            available = 1000
        # Split budget: ~70% full file, ~30% diff
        code_budget = int(available * 0.7)
        diff_budget = available - code_budget
        if len(code) > code_budget:
            code = code[:code_budget] + TRUNCATION_MARKER
        if len(diff) > diff_budget:
            diff = diff[:diff_budget] + TRUNCATION_MARKER
        return template.format(
            system_rules=system_rules,
            filename=filename,
            language=language,
            code=code,
            diff=diff,
        )

    template = DIFF_TEMPLATE if mode == "diff" else FULL_TEMPLATE
    key = "diff" if mode == "diff" else "code"
    if not isinstance(payload, str):
        raise ValueError(f"mode {mode!r} requires a string payload")

    template_overhead = len(
        template.format(
            system_rules=system_rules, filename=filename, language=language, **{key: ""}
        )
    )
    available = max_chars - template_overhead - len(TRUNCATION_MARKER)

    if available <= 0:
        available = 1000

    if len(payload) > available:
        payload = payload[:available] + TRUNCATION_MARKER

    return template.format(
        system_rules=system_rules, filename=filename, language=language, **{key: payload}
    )
