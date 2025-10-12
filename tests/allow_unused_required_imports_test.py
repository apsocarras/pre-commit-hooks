# pyright: reportPrivateUsage = false
import logging
from collections.abc import Callable

import libcst as cst
import pytest
from libcst._nodes.base import CSTNode
from libcst._nodes.statement import Import, ImportFrom
from typing_extensions import Any

from ahooks.hooks.allow_unused_required_imports import (
    _WHITELIST_COMMENT,
    _import_needs_whitelist,
    _importFrom_needs_whitelist,
    _is_missing_whitelist_comment,
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
