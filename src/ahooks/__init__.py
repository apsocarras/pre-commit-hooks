"""
Package for some of the pre-commit hooks I use.

Also includes a helpful utility class for exporting any python script as a pre-commit hook (`HookConfigBlock`)

Run `export_hooks.py` to create a `.pre-commit-config.yaml` from the hooks in this package.
"""

from __future__ import annotations

from beartype import BeartypeStrategy
from beartype.claw import beartype_this_package
from useful_types import (
    SequenceNotStr as Sequence,  # pyright: ignore[reportUnusedImport] # TODO: add a gitcommit hook to append a pyright comment on any required imports in pyproject.toml
)

beartype_this_package()
