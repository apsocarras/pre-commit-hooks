r"""Add `from __future__ import annotations` to `.py` files.

This statement tells the interpreter to treat type hints as string literals,
improving forwards/backwards compatibility between python versions
and simplifying some solutions for achieving type-safety.

    - Most packages which rely on type introspection (e.g. Pydantic) will support this by now
    - Note that PEP 649 will make this statement obsolete (see: https://peps.python.org/pep-0649/)
    - Note also that `ruff` can do this for you with `required-imports` (why did I write this...)
        https://stackoverflow.com/questions/77680073/ignore-specific-rules-in-specific-directory-with-ruff
    - Note the custom filtering I wrote is superfluous with `files=r"^.*\.py$"` and `pass filenames`
     (why did I write this...though this does let you run it as a CLI independent of pre-commit)
"""

from __future__ import annotations

import ast
from collections.abc import Collection
from pathlib import Path
from typing import NamedTuple, cast

import click

from .utils import PreCommitConfigBlock as cb
from .utils._click_utils import READ_DIR_TYPE, stage_if_true
from .utils.git_utils import (
    iter_py_filtered,
)

FROM_FUTURE = "from __future__ import annotations"


IGNORE_DIRS = frozenset[str](
    {
        ".venv",
        "libs",
        "deprecated",
        "_local",
    }
)


class _NodeLoc(NamedTuple):
    idx: int
    lineno: int


def find_insertion_point(mod: ast.Module) -> _NodeLoc | None:
    """Locate where to insert the import statement in the `.py` file

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
            return _NodeLoc(
                idx,
                node.lineno + docstring_offset,
            )
    idx = 0 if not ast.get_docstring(mod) else 1

    return _NodeLoc(idx, docstring_offset)


def _rewrite_file_with_future(src_code: str, path: Path, loc: _NodeLoc) -> None:
    # Add preceding newline only if it's not the first node (i.e. if module has a docstring)
    from_future = f"\n{FROM_FUTURE}\n" if loc.idx != 0 else f"{FROM_FUTURE}\n\n"
    lines = src_code.splitlines(keepends=True)
    lines.insert(loc.lineno, from_future)
    with path.open("w") as file:
        file.writelines(lines)


def _add_statement(path: Path) -> Path | None:
    src_code = path.read_text(encoding="utf-8")
    mod = ast.parse(src_code, filename=str(path))
    loc: _NodeLoc | None = find_insertion_point(mod)
    if loc is None:
        return None
    _rewrite_file_with_future(src_code, path, loc)
    return path


@click.command
@click.argument("proj_root", type=READ_DIR_TYPE, default=Path.cwd())
@click.argument("ignores", nargs=-1, type=READ_DIR_TYPE)
@click.option("--diff-filter-staging", "-ds", is_flag=True)
@click.option("--ignore_by_gitignore", "-g", is_flag=True)
@cb(
    id="add-from-future",
    name="Add `from __future__ import annotations` to `.py` files.",
    language="python",
    entry="python -m ahooks.add_from_future",
    pass_filenames=False,
    stages=["pre-commit"],
    args=["-ds"],
    files=r"^.*\.py$",
)
def main(
    proj_root: Path,
    ignores: Collection[Path] = (),
    diff_filter_staging: bool = True,
    ignore_by_gitignore: bool = False,
) -> None:
    r"""Add `from __future__ import annotations` to `.py` files.

    This statement tells the interpreter to treat type hints as string literals,
    improving forwards/backwards compatibility between python versions
    and simplifying some solutions for achieving type-safety.

        - Most packages which rely on type introspection (e.g. Pydantic) will support this by now
        - Note that PEP 649 will make this statement obsolete (see: https://peps.python.org/pep-0649/)
        - Note also that `ruff` can do this for you with `required-imports` (why did I write this...)
            https://stackoverflow.com/questions/77680073/ignore-specific-rules-in-specific-directory-with-ruff
    - Note the custom filtering I wrote is superfluous with `files=r"^.*\.py$"` and `pass filenames`
     (why did I write this...though this does let you run it as a CLI independent of pre-commit)

    Arguments:
        proj_root : Path
            Path to the Git repository root (or any path within it).
        diff_filter_staging : bool, default=True
            If true, only scan/modify .py files in your .git staging area.
        ignore_by_gitignore : bool, default=False
            Alternative filter which reads files/directories mentioned in your .gitignore
            and excludes any files intersecting with these. Redundant with ``diff_filter_staging``.
        ignores : Ignores -> Collection[str]
            Collection of directory names relative to your project root.
            - Can use as a fallback in case you meant to ignore something in .gitignore but it's not in there.
            - Can also use to ignore files independently of your Git rules.
    """
    root = Path(proj_root)

    gitignore: Path | None = root / ".gitignore" if ignore_by_gitignore else None

    # fmt: off
    added_files: tuple[str, ...] = tuple(
        added.name
        for p in iter_py_filtered(root, diff_filter_staging, gitignore, ignores)
        if (added := _add_statement(p))
    )
    # fmt: on
    stage_if_true(
        len(added_files) > 0,
        "add-from-future",
    )


if __name__ == "__main__":
    main()
