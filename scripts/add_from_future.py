"""
Add `from __future__ import annotations` to `.py` files in your project.

This statement tells the interpreter to treat type hints as string literals,
improving forwards/backwards compatibility between python versions
and simplifying some solutions for achieving type-safety.

See: https://docs.astral.sh/ruff/rules/future-required-type-annotation/.
"""

from __future__ import annotations

import ast
import logging
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Generator, NamedTuple

import click
from typing_extensions import cast

from scripts.utils.git_utils import iter_changed_py_files

logger = logging.getLogger(__name__)


FROM_FUTURE = "from __future__ import annotations"


@lru_cache
def ignore_set(gitignore: Path | None = None) -> set[str]:
    """
    Create set of dirs/path components for this script to ignore.
    Includes all lines in the project's `.gitignore`, if provided.
    """

    ignore_dirs: set[str] = {
        ".venv",
        "libs",
        "deprecated",
        "_local",
    }

    if gitignore is None:
        return ignore_dirs
    if not gitignore.exists():
        warnings.warn(f"{gitignore} not found")
        return ignore_dirs

    def _skip_line(l: str) -> bool:
        return not (ls := l.strip()) or ls.startswith("#") or ls.startswith("!")

    ignore_lines: set[str] = {l for l in gitignore.read_text() if not _skip_line(l)}
    return ignore_lines | ignore_dirs


class NodeLoc(NamedTuple):
    idx: int
    lineno: int


def find_insertion_point(mod: ast.Module) -> NodeLoc | None:
    """
    Assumes:
        - If present, `from __future__ import annotations` is the very first import statement in a module.
        - Docstring is not preceded by any other lines.
    """

    # fmt: off
    docstring_offset = (
        0 
        if not ast.get_docstring(mod)
        else cast(int, mod.body[0].end_lineno)
    )
    # fmt: on

    for idx, node in enumerate(mod.body):
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                return
            return NodeLoc(
                idx,
                node.lineno + docstring_offset,
            )
    idx = 0 if not ast.get_docstring(mod) else 1

    return NodeLoc(idx, docstring_offset)


def rewrite_file_with_future(src_code: str, path: Path, loc: NodeLoc) -> None:
    # Add preceding newline only if it's not the first node (i.e. if module has a docstring)
    from_future = f"\n{FROM_FUTURE}\n" if loc.idx != 0 else f"{FROM_FUTURE}\n\n"
    lines = src_code.splitlines(keepends=True)
    lines.insert(loc.lineno, from_future)
    with path.open("w") as file:
        file.writelines(lines)


def add_statement(path: Path) -> Path | None:
    src_code = path.read_text(encoding="utf-8")
    mod = ast.parse(src_code, filename=str(path))
    loc: NodeLoc | None = find_insertion_point(mod)
    if loc is None:
        return None
    rewrite_file_with_future(src_code, path, loc)
    return path


# fmt: off
def iter_files(root: Path, diff_filter_staging: bool, gitignore: Path | None)  -> Generator[Path, Any, None]:
    """
    - If diff_filter_staging, only iterates over changed .py files in the staging area of .git
    - Else, iterates over all globbed .py files
        - Ignores anything in .venv, libs, deprecated, or _local (folders I commonly use)
        - (Optionally) ignores paths intersecting with anything in .gitignore
    """
    def _in_ignore_set(p: Path) -> bool:
        return any(part in ignore_set(gitignore) for part in p.parts)
    
    def _core_iter() -> Generator[Path, Any, None]: 
        if diff_filter_staging:
            yield from iter_changed_py_files(root) 
        else:         
            yield from root.rglob("**/*.py") 
    
    yield from (p for p in _core_iter() if not _in_ignore_set(p))
# fmt: on


@click.command
@click.argument("proj_root")
@click.option("--ignore_by_gitignore", "-g", is_flag=True)
@click.option("--diff-filter-staging", "-ds", is_flag=True)
def main(
    proj_root: Path | str,
    ignore_by_gitignore: bool = False,
    diff_filter_staging: bool = True,
) -> None:
    root = Path(proj_root)

    gitignore: Path | None = root / ".gitignore" if ignore_by_gitignore else None

    # fmt: off
    added_files: tuple[str, ...] = tuple(
        added.name
        for p in iter_files(root, diff_filter_staging, gitignore)
        if (added := add_statement(p))
    )
    # fmt: on
    if added_files:
        logger.debug(f"Added {FROM_FUTURE} to {len(added_files)} files: {added_files}")


if __name__ == "__main__":
    main()
