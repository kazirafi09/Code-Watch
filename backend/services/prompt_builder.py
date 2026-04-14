from __future__ import annotations

SYSTEM_RULES = """\
You are a precise code reviewer. Your output MUST follow the exact format below. \
Be concise. No filler, no praise, no restating the code. If nothing is wrong in a category, omit it.

Rules:
- Only flag real issues. Do not invent problems to fill sections.
- Each issue: one line, then at most 2 lines of explanation, then a minimal fix snippet if useful.
- Severity must be one of: critical, warning, suggestion.
  - critical = security flaw, data loss, crash, or broken core logic.
  - warning  = likely bug, unsafe pattern, or significant perf issue.
  - suggestion = style, clarity, minor refactor.
- Cite line numbers when visible. Otherwise cite the function or symbol name.
- If the code is clean, output only: "## Summary\\nNo issues found." and stop.

Output format (Markdown, exactly this structure):

## Summary
<one sentence: overall verdict and highest severity present>

## Issues
### [severity] L<line> — <short title>
<=2 lines why it matters.
```{language}
<minimal fix or corrected snippet>
```

(Repeat the ### block per issue, ordered: critical → warning → suggestion. Omit the whole ## Issues section if none.)
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

PORTABLE_PROMPT = """\
You are a precise code reviewer. Review the code below and reply in this exact Markdown format:

## Summary
<one sentence verdict>

## Issues
### [critical|warning|suggestion] L<line> — <title>
<=2 lines why.
```<lang>
<minimal fix>
```

Rules: only real issues, no filler, no praise. Order issues critical → warning → suggestion. \
If clean, output only "## Summary\\nNo issues found."

File: <filename>
Language: <language>

```<language>
<paste code here>
```
"""

TRUNCATION_MARKER = "\n\n... [content truncated due to length] ..."


def build_prompt(
    filename: str,
    language: str,
    mode: str,
    payload: str,
    max_chars: int = 16000,
) -> str:
    template = DIFF_TEMPLATE if mode == "diff" else FULL_TEMPLATE
    key = "diff" if mode == "diff" else "code"
    system_rules = SYSTEM_RULES.format(language=language)

    # Reserve space for the template itself
    template_overhead = len(
        template.format(system_rules=system_rules, filename=filename, language=language, **{key: ""})
    )
    available = max_chars - template_overhead - len(TRUNCATION_MARKER)

    if available <= 0:
        available = 1000

    if len(payload) > available:
        payload = payload[:available] + TRUNCATION_MARKER

    return template.format(
        system_rules=system_rules, filename=filename, language=language, **{key: payload}
    )
