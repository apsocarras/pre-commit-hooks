# pyright: reportPrivateUsage = false
import logging
import os
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Literal, NamedTuple

import libcst as cst
import pytest
from libcst import MetadataWrapper, SimpleStatementLine, metadata
from libcst._nodes.base import CSTNode
from libcst._nodes.statement import Import, ImportFrom, SimpleStatementLine
from libcst.metadata.parent_node_provider import ParentNodeProvider
from typing_extensions import Any, override

from ahooks.hooks.allow_unused_required_imports import (
    _WHITELIST_COMMENT,
    _add_comments,
    _find_matches_raw,
    _get_required_import_statements,
    _import_needs_whitelist,
    _importFrom_needs_whitelist,
    _is_missing_whitelist_comment,
    _line_of,
    _load_toml,
    _with_updated_trailing,
)

logger = logging.getLogger(__name__)


def make_get_trailing_with_comment(
    comment_text: str | None,
):
    """Mock the node visitor's backwards walk"""

    def get_trailing(node: cst.CSTNode) -> cst.TrailingWhitespace | None:
        if comment_text is None:
            return cst.TrailingWhitespace(
                whitespace=cst.SimpleWhitespace(""),
                comment=None,
                newline=cst.Newline(),
            )
        else:
            return cst.TrailingWhitespace(
                whitespace=cst.SimpleWhitespace(" "),
                comment=cst.Comment(f"# {comment_text}"),
                newline=cst.Newline(),
            )

    return get_trailing


def make_env(code: str) -> tuple[Any, Callable[..., CSTNode | None]]:
    comment = code.split("#", maxsplit=1)[-1].strip()
    res_comment = comment or None

    return None, make_get_trailing_with_comment(res_comment)


@pytest.fixture
def meta_env():
    return make_env


def _first_small_stmt(src: str) -> Import | ImportFrom:
    """Parse a module and return the first small statement (Import or ImportFrom)."""
    mod = cst.parse_module(src)
    assert len(mod.body) >= 1
    first = mod.body[0]
    assert isinstance(first, cst.SimpleStatementLine), (
        f"Expected SimpleStatementLine, got {type(first)}"
    )
    assert len(first.body) >= 1
    small = first.body[0]
    assert isinstance(small, (cst.Import, cst.ImportFrom)), (
        f"Expected Import/ImportFrom, got {type(small)}"
    )
    return small


@pytest.mark.parametrize(
    "src,expected",
    [
        ("import os\n", True),
        (f"import os  {_WHITELIST_COMMENT}\n", False),
        ("import os  # some other comment\n", True),
        ("from typing import Any\n", True),
        (f"from typing import Any  {_WHITELIST_COMMENT}\n", False),
    ],
)
def test_is_missing_whitelist_comment(meta_env, src: str, expected: bool):
    _, get_trailing = meta_env(src)
    node = _first_small_stmt(src)
    res = _is_missing_whitelist_comment(node, get_trailing)
    assert res is expected


@pytest.mark.parametrize(
    "test_case_name,import_statement,required_imports,exp_need",
    (
        ("NAME_PRESENT", "import os\n", frozenset({"os"}), True),
        ("MULTIPLE_NAMES_ANY_PRESENT", "import os, sys\n", frozenset({"sys"}), True),
        ("NOT_PRESENT", "import json\n", frozenset({"sys"}), False),
        ("HAS_COMMENT", f"import os {_WHITELIST_COMMENT}\n", frozenset({"os"}), False),
    ),
)
def test_import_needs_whitelist(
    meta_env,
    test_case_name: str,
    import_statement: str,
    required_imports: frozenset[str],
    exp_need: bool,
) -> None:
    _, get_trailing = meta_env(import_statement)
    node = _first_small_stmt(import_statement)
    assert isinstance(node, Import)
    res = _import_needs_whitelist(node, get_trailing, required_imports)
    assert res is exp_need


@pytest.mark.parametrize(
    "test_case_name,import_statement,required_imports,exp_need",
    (
        (
            "SIMPLE_MODULE_REQUIRED",
            "from typing import Any\n",
            frozenset({"typing"}),
            True,
        ),
        (
            "SIMPLE_MODULE_NOT_REQUIRED",
            "from typing import Any\n",
            frozenset({"logging"}),
            False,
        ),
        (
            "HAS_COMMENT",
            f"from typing import Any  {_WHITELIST_COMMENT}\n",
            frozenset({"typing"}),
            False,
        ),
        (
            "DOTTED_MODULE_CURRENT_BEHAVIOR_FALSE",
            "from collections.abc import Iterable\n",
            frozenset({"collections.abc", "collections"}),
            False,
        ),
        (
            "RELATIVE_IMPORT_CURRENT_BEHAVIOR_FALSE",
            "from . import something\n",
            frozenset({"something"}),
            False,
        ),
        (
            "MAIN_USE_CASE",
            "from useful_types import SequenceNotStr as Sequence",
            frozenset(
                (
                    "from __future__ import annotations",
                    "from useful_types import SequenceNotStr as Sequence",
                )
            ),
            True,
        ),
    ),
)
def test_importFrom_needs_whitelist(
    meta_env,
    test_case_name: str,
    import_statement: str,
    required_imports: frozenset[str],
    exp_need: bool,
):
    _, get_trailing = meta_env(import_statement)
    node = _first_small_stmt(import_statement)
    assert isinstance(node, ImportFrom)
    res = _importFrom_needs_whitelist(node, get_trailing, required_imports)
    assert res is exp_need


def test_with_updated_trailing():
    original = cst.parse_statement("x = 1\n")
    assert isinstance(original, cst.SimpleStatementLine)
    assert original.trailing_whitespace.comment is None

    # Act
    updated = _with_updated_trailing(original)

    assert original is not updated
    assert original.trailing_whitespace.comment is None

    assert isinstance(updated.trailing_whitespace.comment, cst.Comment)
    assert updated.trailing_whitespace.comment.value.endswith(_WHITELIST_COMMENT)


class PyProject(NamedTuple):
    path: Path
    imports: frozenset[str]


@pytest.fixture
def example_pyproject(tmpdir: Path) -> PyProject:
    body = textwrap.dedent("""
        [project]
        name = "example"
        version = "0.1.0"
        description = "Add your description here"
        readme = "README.md"
        authors = [
            { name = "Alexander Socarras", email = "apsocarras@gmail.com" }
        ]
        requires-python = ">=3.11"
        dependencies = []

        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [tool.ruff.lint.isort]
        required-imports = [
            "from __future__ import annotations",
            "from useful_types import SequenceNotStr as Sequence # noqa: F401"
        ]
    """)
    path = Path(os.path.join(tmpdir, "example_pyproject.toml"))
    with open(path, "w") as file:
        _ = file.write(body)

    return PyProject(
        path,
        frozenset(
            {
                "from __future__ import annotations",
                "from useful_types import SequenceNotStr as Sequence # noqa: F401",
            }
        ),
    )


class PyModule(NamedTuple):
    raw: str
    processed: str
    required_imports: frozenset[str]


@pytest.fixture
def example_pymodule() -> PyModule:
    raw = textwrap.dedent("""
    import typing
    from __future__ import annotations
    from useful_types import SequenceNotStr as Sequence # noqa: F401

    def foo():
        x = 1
        if x:
            y = 2
            print(y)

    class Bar:
        def method(self):
            z = 3

    if __name__ == "__main__":
        foo()
    """)

    processed = textwrap.dedent("""
    import typing
    from __future__ import annotations
    from useful_types import SequenceNotStr as Sequence # noqa: F401

    def foo():
        x = 1
        if x:
            y = 2
            print(y)

    class Bar:
        def method(self):
            z = 3

    if __name__ == "__main__":
        foo()
    """)
    reqs = frozenset(
        (
            "from __future__ import annotations",
            "from useful_types import SequenceNotStr as Sequence # noqa: F401",
        )
    )
    return PyModule(raw, processed, reqs)


def test_get_required_imports(example_pyproject: PyProject) -> None:
    path, expected_reqs = example_pyproject
    data = _load_toml(path)
    given_reqs = _get_required_import_statements(data)
    assert given_reqs is not None
    assert given_reqs == expected_reqs, given_reqs.symmetric_difference(expected_reqs)


class ParentVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (metadata.ParentNodeProvider,)

    def __init__(self) -> None:
        """Visitor class for testing _walk_back/_lineof"""
        self.import_registry: dict[cst.Import, SimpleStatementLine | None] = {}
        self.importFrom_registry: dict[cst.ImportFrom, SimpleStatementLine | None] = {}

        super().__init__()

    def get_parent(self, node: cst.CSTNode) -> CSTNode | None:
        return self.get_metadata(ParentNodeProvider, node, default=None)

    @override
    def visit_Import(self, node: cst.Import) -> None:
        line: SimpleStatementLine | None = _line_of(node, self.get_parent)
        if line is None:
            logger.error(
                {
                    "event": "import-visit",
                    "status": "error",
                    "details": f"Node missing simple statement: {node.names}",
                }
            )
        else:
            logger.debug(
                {
                    "event": "import-visit",
                    "status": "success",
                }
            )
        self.import_registry[node] = line

    @override
    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        line: SimpleStatementLine | None = _line_of(node, self.get_parent)
        if line is None:
            logger.error(
                {
                    "event": "importFrom-visit",
                    "status": "error",
                    "details": f"Node missing simple statement: {node.names}",
                }
            )
        else:
            logger.debug(
                {
                    "event": "importFrom-visit",
                    "status": "success",
                }
            )

        self.importFrom_registry[node] = line

    def has(self, node: cst.CSTNode) -> bool:
        if isinstance(node, cst.ImportFrom):
            return node in self.importFrom_registry
        return node in self.import_registry

    def get_line(self, node: cst.CSTNode) -> SimpleStatementLine | None:
        if isinstance(node, cst.ImportFrom):
            return self.importFrom_registry.get(node)
        if isinstance(node, cst.Import):
            return self.import_registry.get(node)
        return None


@pytest.mark.parametrize("node_type", ("IMPORT_FROM", "IMPORT"))
def test_walk_back_finds_enclosing_lines(
    example_pymodule: PyModule, node_type: Literal["IMPORT_FROM", "IMPORT"]
) -> None:
    mod = cst.parse_module(example_pymodule.raw)
    wrapper = MetadataWrapper(mod)
    visitor = ParentVisitor()
    mod_visit = wrapper.visit(visitor)

    if node_type == "IMPORT":
        matches = _find_matches_raw(mod_visit, cst.Import)
        assert all(isinstance(x, cst.Import) for x in matches)
    else:
        matches = _find_matches_raw(mod_visit, cst.ImportFrom)
        assert all(isinstance(x, cst.ImportFrom) for x in matches)
    assert matches

    missing_nodes = tuple(node for node in matches if not visitor.has(node))
    assert not missing_nodes, len(matches) - len(missing_nodes)
    nodes_missing_lines = tuple(node for node in matches if not visitor.get_line(node))
    assert not nodes_missing_lines, len(matches) - len(nodes_missing_lines)


def test_add_comment(example_pymodule: PyModule):
    mod = cst.parse_module(example_pymodule.raw)
    _new_mod, changed = _add_comments(
        mod, required_imports=example_pymodule.required_imports
    )
    assert changed
