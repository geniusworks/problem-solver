"""The repository's .gitignore keeps local data out of commits, whatever form it takes.

A worktree links venv and years to the main checkout. Rules written as `venv/` or `years/*`
match a directory and its contents but not a symlink of that name, so `git add -A` in a
worktree committed both links, and pulling that commit into the main checkout replaced the
real directories with them.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _untracked(repo: Path) -> set:
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout
    return {line[3:] for line in out.splitlines()}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    shutil.copy(REPO / ".gitignore", tmp_path / ".gitignore")
    return tmp_path


def test_venv_and_years_linked_from_a_worktree_are_ignored(repo: Path, tmp_path_factory):
    target = tmp_path_factory.mktemp("main_checkout")
    (target / "venv").mkdir()
    (target / "years").mkdir()
    (repo / "venv").symlink_to(target / "venv")
    (repo / "years").symlink_to(target / "years")

    assert _untracked(repo) == {".gitignore"}


def test_venv_and_years_directories_are_ignored(repo: Path):
    (repo / "venv" / "bin").mkdir(parents=True)
    (repo / "venv" / "bin" / "python").write_text("")
    (repo / "years" / "2024" / "day01").mkdir(parents=True)
    (repo / "years" / "2024" / "day01" / "input.txt").write_text("1\n")
    (repo / "years" / "2024" / "day01" / "answers.json").write_text("{}\n")

    assert _untracked(repo) == {".gitignore"}
