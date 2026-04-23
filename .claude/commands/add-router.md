# /add-router — Scaffold a new FastAPI router

Use this when adding a new router to `backend/routers/`.

## Steps

1. **Create** `backend/routers/<name>.py` following this pattern:
```python
from fastapi import APIRouter, HTTPException
from backend.core.database import <needed_helpers>

router = APIRouter()

@router.get("/")
async def list_items():
    ...

@router.post("/")
async def create_item():
    ...
```

2. **Mount** in `backend/main.py`:
```python
from backend.routers.<name> import router as <name>_router
app.include_router(<name>_router, prefix="/api/<name>", tags=["<name>"])
```

3. **Frontend client** — add typed fetch wrappers in `frontend/src/api/client.ts` and matching TS types in `frontend/src/api/types.ts`.

## Conventions
- Use `pathlib.Path` for any file paths; normalize to POSIX slashes before returning to frontend.
- DB calls use free functions from `backend/core/database.py` — no dependency injection needed.
- Raise `HTTPException(status_code=404)` for missing resources, `422` for validation errors (FastAPI handles the latter automatically via Pydantic).
