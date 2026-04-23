# /lint — Lint and format

Run ruff check then ruff format on backend and tests.

```bash
ruff check backend/ tests/
ruff format backend/ tests/
```

Fix all auto-fixable issues with:
```bash
ruff check --fix backend/ tests/
```
