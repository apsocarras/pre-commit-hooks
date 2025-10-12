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
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

import click
import libcst as cst
from libcst import metadata
from libcst._nodes.expression import BaseExpression
from libcst._nodes.statement import SimpleStatementLine
from libcst._nodes.whitespace import TrailingWhitespace
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


_attrs = ()

_T_Import = TypeVar("_T_Import", bound=cst.Import | cst.ImportFrom)

_T_Stop = TypeVar("_T_Stop", bound=cst.CSTNode)


def _walk_back(
    node: cst.CSTNode,
    get_meta,
    stop_type: type[_T_Stop],
) -> _T_Stop | None:
    cur = node
    while True:
        parent = get_meta(metadata.ParentNodeProvider, cur)
        if parent is None:
            return None
        if isinstance(parent, stop_type):
            return parent
        cur = parent


def _line_of(node: cst.CSTNode, get_meta) -> SimpleStatementLine | None:
    return _walk_back(node, get_meta, cst.SimpleStatementLine)


P = ParamSpec("P")
WhiteSpaceFinder = Callable[P, TrailingWhitespace | None]


def _get_trailing(
    node: cst.Import | cst.ImportFrom, get_meta
) -> TrailingWhitespace | None:
    enclosing_line: SimpleStatementLine | None = _line_of(node, get_meta)
    if enclosing_line is None:
        return None
    return enclosing_line.trailing_whitespace


def _is_missing_whitelist_comment(
    node: _T_Import,
    get_trailing: WhiteSpaceFinder[_T_Import],
) -> bool:
    trailing = get_trailing(node)
    return (
        trailing is None
        or not trailing.comment
        or _WHITELIST_COMMENT not in trailing.comment.value
    )


def _import_needs_whitelist(
    node: cst.Import,
    get_trailing: WhiteSpaceFinder[cst.Import],
    required_imports: frozenset[str],
) -> bool:
    return any(
        name in required_imports for name in _node_names(node)
    ) and _is_missing_whitelist_comment(node, get_trailing)


def _importFrom_needs_whitelist(
    node: cst.ImportFrom,
    get_trailing: WhiteSpaceFinder[cst.ImportFrom],
    required_imports: frozenset[str],
) -> bool:
    if not isinstance(node.module, cst.Name):
        return False
    modname = node.module.value
    return modname in required_imports and _is_missing_whitelist_comment(
        node, get_trailing
    )


def _register_import(
    node: cst.Import,
    get_trailing: WhiteSpaceFinder[cst.Import],
    required_imports: frozenset[str],
    register: Callable[[SimpleStatementLine | None], Any],
) -> None:
    """Mark an Import's enclosing simple line statement as needing a whitelist comment."""
    if _import_needs_whitelist(node, get_trailing, required_imports):
        enclosure = _line_of(node, get_meta)
        register(enclosure)


def _register_importFrom(
    node: cst.ImportFrom,
    get_trailing: WhiteSpaceFinder[cst.ImportFrom],
    required_imports: frozenset[str],
    register: Callable[[SimpleStatementLine | None], Any],
) -> None:
    """Mark an ImportFrom's enclosing simple line statement as needing a whitelist comment."""
    if _importFrom_needs_whitelist(node, get_trailing, required_imports):
        enclosure = _line_of(node, get_meta)
        register(enclosure)


def _with_updated_trailing(node: SimpleStatementLine) -> SimpleStatementLine:
    tw = node.trailing_whitespace
    new_tw = tw.with_changes(comment=cst.Comment(f" {_WHITELIST_COMMENT}"))
    return node.with_changes(trailing_whitespace=new_tw)


class _AppendWhiteListComment(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (metadata.ParentNodeProvider,)

    def __init__(self, required_imports: frozenset[str]) -> None:
        self.required_imports: frozenset[str] = required_imports
        self.changed: bool = False
        self._line_registry: set[int] = set()
        super().__init__()

    def get_meta(self, provider, node):
        return self.get_metadata(provider, node)

    def get_trailing(self, node) -> TrailingWhitespace | None:
        return _get_trailing(node, self.get_meta)

    def register_line(self, line: SimpleStatementLine | None) -> None:
        if line is not None:
            return self._line_registry.add(id(line))

    def line_needs_comment(self, line: SimpleStatementLine) -> bool:
        return id(line) in self._line_registry

    @override
    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        _register_importFrom(
            node, self.get_trailing, self.required_imports, self.register_line
        )

    @override
    def visit_Import(self, node: cst.Import) -> None:
        _register_import(
            node, self.get_trailing, self.required_imports, self.register_line
        )

    @override
    def leave_SimpleStatementLine(
        self, original_node: SimpleStatementLine, updated_node: SimpleStatementLine
    ):
        if not self.line_needs_comment(original_node):
            return updated_node
        return _with_updated_trailing(updated_node)


def _add_comments(
    mod: cst.Module, required_imports: frozenset[str]
) -> tuple[cst.Module, bool]:
    """Apply the # noqa: F401 comments to matching import lines."""
    transformer = _AppendWhiteListComment(required_imports)
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
