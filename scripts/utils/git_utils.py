from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from typing_extensions import LiteralString, override


def run_git(cwd: Path, *args: str) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{res.stderr.strip()}")
    return res.stdout


def find_repo_root(start: Path) -> Path:
    """Find the .git repo root from a starting directory"""
    try:
        out = run_git(start, "rev-parse", "--show-toplevel")
        return Path(out.strip())
    except Exception:
        # Fallback: assume provided root is the repo root
        return start


DiffFilterType = Literal["A", "C", "M", "R", "T", "U", "X", "B", "D"]


class DiffFilter:
    def __init__(self, *args: DiffFilterType) -> None:
        self._cmd: LiteralString = f"--diff-filter={''.join(args)}"

    @override
    def __str__(self) -> str:
        return self._cmd


IGNORE_DELETE = DiffFilter("A", "C", "M", "R", "T", "U", "X", "B")


def iter_changed_py_files(
    root: Path,
    *,
    staged: bool = True,
    working_tree: bool = False,
    base: str | None = None,
    diff_filter: DiffFilter = IGNORE_DELETE,
) -> Iterable[Path]:
    """
    Arguments:
        root : Path
            Path to the Git repository root (or any path within it).
        staged : bool, default=True
            If True, show changes staged in the index (equivalent to
            `git diff --cached`).
        working_tree : bool, default=False
            If True, show unstaged changes in the working directory
            (equivalent to `git diff`). Overrides `staged`.
        base : str, optional
            A Git ref or commit to compare against (e.g. "origin/main").
            If provided, diffs are computed against this ref:
            * staged=True  → `git diff --cached base`
            * staged=False → `git diff base`

    Returns:
        Iterable[Path] :
            Absolute paths to `.py` files matching your filter criteria.
    """

    def _cmd(*args: str):
        return run_git(root, "diff", "--name-only", str(diff_filter), *args)

    if base:
        args = ("--cached", base) if staged else (base,)
        out = _cmd(*args)
    elif working_tree:
        out = _cmd()
    elif staged:
        out = _cmd("--cached")
    else:
        # default to staged files
        out = _cmd("--cached")

    # fmt: off
    for rel in out.splitlines():
        if rel.endswith(".py") \
        and (p := (root / rel).resolve()).exists():
            yield p
    # fmt: on
