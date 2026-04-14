from __future__ import annotations

from pathlib import Path


def test_gitignore_matches_ignored_file(temp_project_dir):
    from backend.utils.gitignore import GitignoreMatcher

    gitignore = temp_project_dir / ".gitignore"
    gitignore.write_text("*.log\nbuild/\n")

    matcher = GitignoreMatcher(temp_project_dir)

    log_file = temp_project_dir / "app.log"
    log_file.touch()
    assert matcher.is_ignored(log_file, temp_project_dir)

    build_file = temp_project_dir / "build" / "output.js"
    build_file.parent.mkdir()
    build_file.touch()
    assert matcher.is_ignored(build_file, temp_project_dir)


def test_gitignore_allows_non_ignored_file(temp_project_dir):
    from backend.utils.gitignore import GitignoreMatcher

    gitignore = temp_project_dir / ".gitignore"
    gitignore.write_text("*.log\n")

    matcher = GitignoreMatcher(temp_project_dir)

    py_file = temp_project_dir / "main.py"
    py_file.touch()
    assert not matcher.is_ignored(py_file, temp_project_dir)


def test_no_gitignore_ignores_nothing(temp_project_dir):
    from backend.utils.gitignore import GitignoreMatcher

    matcher = GitignoreMatcher(temp_project_dir)
    any_file = temp_project_dir / "anything.py"
    any_file.touch()
    assert not matcher.is_ignored(any_file, temp_project_dir)
