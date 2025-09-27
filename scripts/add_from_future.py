"""
Tell interpreter to treat type hints as string literals. Improves forwards/backwards compatibility between python versions.

See: https://docs.astral.sh/ruff/rules/future-required-type-annotation/
"""

from __future__ import annotations

import ast
import logging
import warnings
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)

PROJ_ROOT = Path(__file__).parent.parent

FROM_FUTURE = "from __future__ import annotations"


class WrongLineWarning(UserWarning):
    """
    If present, `from __future__ import annotations` should be the very first import statement in a module.

    The `ruff` linter settings configured in pyproject.toml will flag as an error if that import is on
    a later line in the module.
    """

    def __init__(self, mod: ast.Module, lineno: int, *args: object) -> None:
        msg = f"`{FROM_FUTURE}` not the first non-docstring statement of module {mod} (line: {lineno})"
        super().__init__(msg, *args)


class NodeLoc(NamedTuple):
    idx: int
    lineno: int


def locate_first_import_statement(mod: ast.Module) -> NodeLoc | None:
    for idx, node in enumerate(mod.body):
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                return None
            return NodeLoc(
                idx,
                node.lineno,
            )
    return NodeLoc(0, 0)


def rewrite_file_with_future(src_code: str, path: Path, insertion_lineno: int) -> None:
    lines = src_code.splitlines(keepends=True)
    lines.insert(insertion_lineno, f"\n{FROM_FUTURE}\n")
    with path.open("w") as file:
        file.writelines(lines)


def add_statement(path: Path) -> Path | None:
    src_code = path.read_text(encoding="utf-8")
    mod = ast.parse(src_code, filename=str(path))
    loc: NodeLoc | None = locate_first_import_statement(mod)
    if loc is None:
        return None
    if loc.idx > 1:
        warnings.warn(WrongLineWarning(mod, loc.lineno))
    rewrite_file_with_future(src_code, path, loc.lineno)
    return path


IGNORE_DIRS: set[str] = {
    ".venv",
    "libs",
    "deprecated",
    "_local",
}


def _in_ignore(p: Path):
    return any(part in IGNORE_DIRS for part in p.parts)


def main() -> None:
    # fmt: off
    added_files: tuple[str, ...] = tuple(
        added.name
        for path in PROJ_ROOT.rglob("**/*.py")
        if not _in_ignore(path)
        if (added := add_statement(path))
    )
    # fmt: on
    if added_files:
        logger.debug(f"Added {FROM_FUTURE} to {len(added_files)} files: {added_files}")


if __name__ == "__main__":
    main()
