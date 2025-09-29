from __future__ import annotations

import subprocess
import warnings
from collections.abc import Collection, Iterable
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Callable, Literal, TypeVar, Union, cast

from typing_extensions import LiteralString, Self, TypeAlias, override

Ignores: TypeAlias = Annotated[
    Union[Collection[str], Collection[Path]],
    "Collection of files or directories for this hook to skip.",
]
PathLike = Union[str, Path]


def run_git(cwd: Path, *args: str) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{res.stderr.strip()}")
    return res.stdout


def git_add(path: Path) -> None:
    _ = subprocess.run(
        ("git", "add", "--", str(path)),
        check=False,
        capture_output=True,
    )


@lru_cache
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


@lru_cache
def ignore_set(ignores: Ignores, gitignore: Path | None = None) -> frozenset[Path]:
    """Create set of dirs or file paths to ignore.

    - Can be used to ignore artbitrary files independent of your `.git` repo structure.
    - Includes all lines in the `.gitignore`, if provided.

    Note:
        With` @lru_cache` it is a good idea to always use the same type of collection when passing in ``ignores``
    """

    def _normalize(paths: Collection[PathLike]) -> frozenset[Path]:
        return frozenset(Path(p) for p in paths)

    if gitignore is None:
        return _normalize(ignores)

    if not gitignore.exists():
        warnings.warn(f"{gitignore} not found", stacklevel=2)
        return _normalize(ignores)

    ignore_lines: frozenset[Path] = frozenset(
        Path(l) for l in iter_gitignore(gitignore)
    )
    return ignore_lines | _normalize(ignores)


def in_ignore_set(
    p: PathLike, ignores: Ignores, gitignore: PathLike | None = None
) -> bool:
    path = Path(p)
    ig = ignore_set(tuple(ignores), gitignore)
    return (path in ig) or any(parent in ig for parent in path.parents)


class IgnoreSet(frozenset[Path]):
    """Class API for `ignore_set`"""

    @override
    def __new__(cls, ignores: Ignores, gitignore: Path | None = None) -> Self:
        return super().__new__(cls, ignore_set(tuple(ignores), gitignore))

    @override
    def __contains__(self, o: object, /) -> bool:
        if isinstance(o, Path):
            return o in self or any(parent in self for parent in o.parents)
        return False


def iter_py_git_diff(
    root: Path,
    *,
    staging_area: bool = True,
    working_tree: bool = False,
    base: str | None = None,
    diff_filter: DiffFilter = IGNORE_DELETE,
) -> Iterable[Path]:
    """Iterate over changed `.py` files per specified Git filters.

    Arguments:
        root : Path Path to the Git repository root (or any path within it).
        staging_area : bool, default=True
            → `git diff --cached`
        working_tree : bool, default=False
            → `git diff`
        base : str, optional, default=None
            A Git ref or commit to compare against (e.g. "origin/main").
            * staged=True  → `git diff --cached base`
            * staged=False → `git diff base`
        diff_filter : DiffFilter, default=IGNORE_DELETE,


    Returns:
        Iterable[Path] :
            Absolute paths to `.py` files matching your diff-filter criteria.
    """
    repo_root: Path = find_repo_root(root)

    def _cmd(*args: str):
        return run_git(repo_root, "diff", "--name-only", str(diff_filter), *args)

    if base:
        args = ("--cached", base) if staging_area else (base,)
        out = _cmd(*args)
    elif working_tree:
        out = _cmd()
    elif staging_area:
        out = _cmd("--cached")
    else:
        # default to staged files
        out = _cmd("--cached")

    # fmt: off
    for rel in out.splitlines():
        if rel.endswith(".py") \
        and (p := (root / rel).absolute()).exists():
            yield p
    # fmt: on


def iter_py_filtered(
    root: Path, diff_filter_staging: bool, gitignore: Path | None, ignores: Ignores
) -> Iterable[Path]:
    """Iterate over Python source files under a project root with optional filtering.

    Args:
        root (Path): Root directory of the project.
        diff_filter_staging (bool):
            If True, yield only changed `.py` files from the Git staging area.
            If False, recursively glob all `.py` files under ``root``.
        gitignore (Path | None):
            Optional path to a `.gitignore` file.
            - If provided and exists, its rules will be included in the ignore set.
        ignores (Ignores):
            A collection of directories/files to exclude.

    Yields:
        Path: File paths of Python source files not excluded by the ignore rules.
    """

    def _core_iter() -> Iterable[Path]:
        if diff_filter_staging:
            yield from iter_py_git_diff(root, staging_area=diff_filter_staging)
        else:
            yield from root.rglob("*.py")

    yield from (p for p in _core_iter() if not in_ignore_set(root, ignores, gitignore))


# fmt: off
def _non_ignore(l: str) -> bool:
    return not (ls := l.strip()) \
        or ls.startswith("#") \
        or ls.startswith("!")
# fmt: on


def iter_gitignore(
    path: Path | str, line_skip: Callable[[str], bool] = _non_ignore
) -> Iterable[str]:
    with open(path) as file:
        for line in iter(file.readline, ""):
            if not line_skip(line):
                yield line


T = TypeVar("T", str, Path)


# fmt: off
def check_ignored(
    root: Path, ignore: T | Collection[T]
) -> set[T]:
# fmt: on
    start = find_repo_root(root)
    if isinstance(ignore, (Path, str)):
        result = run_git(start, "check-ignore", str(ignore))
        if str(ignore) in result:
            return {cast(T, ignore)}
        return set()
    else:
        result = run_git(start, "check-ignore", *(str(r) for r in ignore))
        cls_ = next(iter(ignore)).__class__
        result_set = {cls_(r) for r in result.splitlines()}
        return result_set.intersection(ignore)
