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

import ast
import logging
from pathlib import Path
from typing import Any

import click
from useful_types import (
    SequenceNotStr as Sequence,  # pyright: ignore[reportUnusedImport]
)

from ahooks._types import OpSentinel

logger = logging.getLogger(__name__)

_WHITELIST_COMMENT = "# noqa: F401"


def _load_toml(toml_file: Path) -> dict[str, Any]:
    import tomli

    toml = tomli.loads(toml_file.read_text("utf-8"))
    return toml


def _get_required_import_statements(toml_data: dict[str, Any]) -> tuple[str, ...]: ...


def _is_required_import_statement(node: ast.AST) -> bool: ...


def _apply_comment_in_place(node: ast.AST, /) -> OpSentinel: ...


def _add_comments(mod: ast.Mod) -> OpSentinel: ...


@click.command
def allow_unused_required_imports() -> None:
    """Tell ruff to allow unused imports for any imports listed in the required-imports entry

    This hook automatically applies the `# noqa: F401` comment to all import lines required by ruff.
    """
