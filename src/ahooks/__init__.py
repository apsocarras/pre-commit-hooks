"""
Package for some of the pre-commit hooks I use.

Also includes a helpful utility class for exporting any python script as a pre-commit hook (`HookConfigBlock`)

Run `export_hooks.py` to create a `.pre-commit-config.yaml` from the hooks in this package.
"""

from __future__ import annotations

import warnings

from beartype.claw import beartype_this_package
from nobeartype import NoBearType
from rich.console import Console
from useful_types import (
    SequenceNotStr as Sequence,  # pyright: ignore[reportUnusedImport] # TODO: add a gitcommit hook to append a pyright comment on any required imports in pyproject.toml
)

console = Console()


def _rich_warning(message, category, filename, lineno, file=None, line=None):  # type: ignore[no-untyped-def]
    console.print(f"[bold yellow]{category.__name__}[/bold yellow]: {message}")


warnings.showwarning = _rich_warning


beartype_this_package()
nobeartype = NoBearType()
