from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pathspec

    _PATHSPEC_AVAILABLE = True
except ImportError:
    _PATHSPEC_AVAILABLE = False
    logger.warning("pathspec not installed — .gitignore support disabled")


class GitignoreMatcher:
    def __init__(self, project_root: Path) -> None:
        self._spec = None
        if not _PATHSPEC_AVAILABLE:
            return
        gitignore = project_root / ".gitignore"
        if not gitignore.exists():
            return
        try:
            patterns = gitignore.read_text(encoding="utf-8").splitlines()
            self._spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        except Exception:
            logger.exception("Failed to parse .gitignore at %s", gitignore)

    def is_ignored(self, path: Path, project_root: Path) -> bool:
        if self._spec is None:
            return False
        try:
            rel = path.relative_to(project_root)
            return self._spec.match_file(str(rel).replace("\\", "/"))
        except ValueError:
            return False
