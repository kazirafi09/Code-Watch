# /test — Run tests

Usage: `/test [optional filter]`

```bash
# All tests
pytest

# Single file
pytest tests/<file>.py

# Single test
pytest tests/<file>.py::<test_name>

# With output
pytest -s tests/<file>.py
```

The `$ARGUMENTS` passed after `/test` should be appended directly to the pytest command.

Always activate the venv first: `source .venv/bin/activate` (Unix) or `.venv\Scripts\activate` (Windows).
