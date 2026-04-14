from __future__ import annotations
import difflib
import hashlib
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# In-memory caches keyed by (project_id, path_str).
_last_hash: dict[tuple[int, str], str] = {}
_last_content: dict[tuple[int, str], str] = {}


def _hash(content: str) -> str:
    encoded = content.encode("utf-8", errors="replace")
    return hashlib.sha256(encoded).hexdigest()


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _git_diff(project_path: Path, file_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", str(file_path)],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except Exception:
        pass
    return None


def compute_diff(
    project_id: int,
    project_path: Path,
    file_path: Path,
    current_content: str,
) -> tuple[str, str]:
    """
    Returns (mode, payload):
      - ("full", content)  — first review or no previous snapshot
      - ("diff", diff_text) — subsequent reviews with changes
    """
    key = (project_id, str(file_path))
    current_hash = _hash(current_content)

    if key not in _last_content:
        # First review — store snapshot and return full content
        _last_content[key] = current_content
        _last_hash[key] = current_hash
        return "full", current_content

    previous_content = _last_content[key]

    # Try git diff first
    if _is_git_repo(project_path):
        git_diff = _git_diff(project_path, file_path)
        if git_diff:
            _last_content[key] = current_content
            _last_hash[key] = current_hash
            return "diff", git_diff

    # Fall back to unified diff
    prev_lines = previous_content.splitlines(keepends=True)
    curr_lines = current_content.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            prev_lines,
            curr_lines,
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
            lineterm="",
        )
    )

    _last_content[key] = current_content
    _last_hash[key] = current_hash

    if not diff_lines:
        return "full", current_content

    return "diff", "\n".join(diff_lines)


def get_last_hash(project_id: int, file_path: Path) -> str | None:
    return _last_hash.get((project_id, str(file_path)))


def clear_cache(project_id: int) -> None:
    keys_to_delete = [k for k in _last_content if k[0] == project_id]
    for k in keys_to_delete:
        del _last_content[k]
        _last_hash.pop(k, None)
