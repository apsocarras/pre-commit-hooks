"""Tell ruff to allow unused imports for any imports listed in the required-imports entry.

In a pyproject.toml or ruff config file, you can tell ruff to require certain imports:

```pyrproject.toml
[tool.ruff.lint.isort]
required-imports = [
    "from useful_types import SequenceNotStr as Sequence # noqa: F401"
]
```

(Requiring this import is the lightest-weight solution I've found to the infamous `Sequence[str]` footgun)

Unfortunately, you can't also tell it to ignore unused import rules on those require import lines:

```pycon
# Notice the comment not included
>>> from useful_types import SequenceNotStr as Sequence

```

This hook automatically applies the `# noqa: F401` comment to all import lines required by ruff

"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar, cast

import click
import libcst as cst
from libcst._nodes.expression import BaseExpression
from libcst._nodes.whitespace import TrailingWhitespace
from libcst.metadata import PositionProvider
from typing_extensions import override
from useful_types import (
    SequenceNotStr as Sequence,  # pyright: ignore[reportUnusedImport]
)

from ahooks.utils._file_utils import write_atomic

from ..models import HookConfigBlock as cb
from ..utils._click_utils import (
    READ_FILE_TYPE,
    NoRequiredImportsException,
    stage_if_true,
)

logger = logging.getLogger(__name__)

_WHITELIST_COMMENT = "# noqa: F401"


def _load_toml(toml_file: Path) -> dict[str, Any]:
    import tomli

    toml = tomli.loads(toml_file.read_text("utf-8"))
    return toml


def _get_required_import_statements(toml_data: dict[str, Any]) -> frozenset[str] | None:
    try:
        return frozenset(toml_data["tool"]["ruff"]["lint"]["isort"]["required-imports"])
    except KeyError:
        return None


def _node_names(node: cst.Import) -> set[BaseExpression | str]:
    return {n.name.value for n in node.names}


def _get_trailing(node: cst.Import | cst.ImportFrom) -> TrailingWhitespace:
    """Type safe access of the trailing_whitespace attribute"""
    return cast(cst.TrailingWhitespace, getattr(node, "trailing_whitespace"))  # noqa: B009


def _is_missing_whitelist_comment(node: cst.Import | cst.ImportFrom) -> bool:
    trailing = _get_trailing(node)
    return not trailing.comment or _WHITELIST_COMMENT not in trailing.comment.value


def _import_needs_whitelist(node: cst.Import, required_imports: frozenset[str]) -> bool:
    return any(
        name in required_imports for name in _node_names(node)
    ) and _is_missing_whitelist_comment(node)


def _importFrom_needs_whitelist(
    node: cst.ImportFrom, required_imports: frozenset[str]
) -> bool:
    if not isinstance(node.module, cst.Name):  # TODO: what case is this?
        return False
    modname = node.module.value
    return modname in required_imports and _is_missing_whitelist_comment(node)


T = TypeVar("T", cst.Import, cst.ImportFrom)


def _append_comment(node: T, /) -> T:
    new_trailing = _get_trailing(node).with_changes(
        comment=cst.Comment(f" {_WHITELIST_COMMENT}")
    )
    return node.with_changes(trailing_whitespace=new_trailing)


class _NoqaTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, required_imports: frozenset[str]) -> None:
        self.required_imports: frozenset[str] = required_imports
        self.changed: bool = False
        super().__init__()

    @override
    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import:
        if not _import_needs_whitelist(updated_node, self.required_imports):
            return updated_node

        self.changed = True
        return _append_comment(updated_node)

    @override
    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        if not _importFrom_needs_whitelist(updated_node, self.required_imports):
            return updated_node

        self.changed = True
        return _append_comment(updated_node)


def _add_comments(
    mod: cst.Module, required_imports: frozenset[str]
) -> tuple[cst.Module, bool]:
    """Apply the # noqa: F401 comments to matching import lines."""
    transformer = _NoqaTransformer(required_imports)
    new_mod = mod.visit(transformer)
    return new_mod, transformer.changed


def _process_files(files: Iterable[Path], reqs: frozenset[str]) -> Iterable[Path]:
    for f in files:
        source = f.read_text("utf-8")
        mod = cst.parse_module(source)
        new_mod, changed = _add_comments(mod, reqs)
        if changed:
            write_atomic(f, new_mod.code)
            yield f


@click.command
@click.argument("files")
@click.option("--pyproject", type=READ_FILE_TYPE, default="pyproject.toml")
@cb(
    id="allow-unused-required-imports",
    name="Tell ruff to allow unused imports for any imports listed in the required-imports entry",
    language="system",
    entry="python -m ahooks.allow_unused_required_imports",
    pass_filenames=True,
    stages=("pre-commit",),
    args=("-ds",),
    files=r"^.*\.py$",
)
def allow_unused_required_imports(
    files: tuple[
        Path, ...
    ],  # TODO: should be typed to match pre-commit's passing of file names
    pyproject: Path,
) -> None:
    """Tell ruff to allow unused imports for any imports listed in the required-imports entry

    This hook automatically applies the `# noqa: F401` comment to all import lines required by ruff.
    """
    toml_data = _load_toml(pyproject)
    reqs = _get_required_import_statements(toml_data)
    if reqs is None:
        raise NoRequiredImportsException()

    changed_files = tuple(_process_files(files, reqs))

    stage_if_true(
        len(changed_files) > 0, "allow-unused-required-imports", *changed_files
    )


if __name__ == "__main__":
    allow_unused_required_imports()
