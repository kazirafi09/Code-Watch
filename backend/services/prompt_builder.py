from __future__ import annotations

FULL_TEMPLATE = """\
You are an expert code reviewer. Review the following code for:
1. Bugs and logic errors
2. Security vulnerabilities
3. Performance issues
4. Code quality and maintainability
5. Specific improvements with examples

File: {filename}
Language: {language}

```{language}
{code}
```

Respond with a structured review. For each issue found, state: severity (critical/warning/suggestion), \
location (line number if possible), and a concrete fix.
"""

DIFF_TEMPLATE = """\
You are an expert code reviewer. Review the following code changes for:
1. Bugs and logic errors
2. Security vulnerabilities
3. Performance issues
4. Code quality and maintainability
5. Specific improvements with examples

File: {filename}
Language: {language}

Focus primarily on the changed lines (marked with + and -) while also flagging anything risky in the \
surrounding context.

```diff
{diff}
```

Respond with a structured review. For each issue found, state: severity (critical/warning/suggestion), \
location (line number if possible), and a concrete fix.
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

    # Reserve space for the template itself
    template_overhead = len(template.format(filename=filename, language=language, **{key: ""}))
    available = max_chars - template_overhead - len(TRUNCATION_MARKER)

    if available <= 0:
        available = 1000

    if len(payload) > available:
        payload = payload[:available] + TRUNCATION_MARKER

    return template.format(filename=filename, language=language, **{key: payload})
