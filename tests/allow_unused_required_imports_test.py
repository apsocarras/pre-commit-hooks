# pyright: reportPrivateUsage = false
import logging
from collections.abc import Callable
from functools import cache
from typing import Any

import libcst as cst
import pytest
from libcst import metadata
from libcst._nodes.statement import Import, ImportFrom
from libcst.metadata.wrapper import MetadataWrapper

from ahooks.hooks.allow_unused_required_imports import (
    _WHITELIST_COMMENT,
    _import_needs_whitelist,
    _importFrom_needs_whitelist,
    _is_missing_whitelist_comment,
)

logger = logging.getLogger(__name__)


def make_get_meta(wrapper: metadata.MetadataWrapper):
    """Create a mock get_meta function which does not throw on a missing key"""

    @cache
    def _resolve(provider):
        return wrapper.resolve(provider)

    def _get_meta(provider, node):
        mapping = _resolve(provider)
        try:
            return mapping[node]
        except KeyError:
            return None

    return _get_meta


def make_env(code: str) -> tuple[MetadataWrapper, Callable[..., Any]]:
    wrapper = metadata.MetadataWrapper(cst.parse_module(code))

    get_meta = make_get_meta(wrapper)

    return wrapper, get_meta


@pytest.fixture
def meta_env() -> Callable[..., tuple[MetadataWrapper, Callable[..., Any]]]:
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
def test_is_missing_whitelist_comment(src: str, expected: bool, meta_env):
    _wrapper, get_meta = meta_env(src)
    node = _first_small_stmt(src)
    assert _is_missing_whitelist_comment(node, get_meta) is expected


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
    _wrapper, get_meta = meta_env(import_statement)
    node = _first_small_stmt(import_statement)
    assert isinstance(node, Import)
    res = _import_needs_whitelist(node, get_meta, required_imports)
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
    _wrapper, get_meta = meta_env(import_statement)
    node = _first_small_stmt(import_statement)
    assert isinstance(node, ImportFrom)
    res = _importFrom_needs_whitelist(node, get_meta, required_imports)
    assert res is exp_need
