"""Enabling runtime type-checking on all tests with beartype_package("ahooks")"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterator

from beartype.claw import beartype_package
from useful_types import SequenceNotStr as Sequence

beartype_package("ahooks")


def _iter_modules() -> Iterator[pkgutil.ModuleInfo]:
    pkg = importlib.import_module("ahooks")
    return pkgutil.walk_packages(pkg.__path__, pkg.__name__ + ".")


def test_import_all_package_modules():
    """Iterate over all package modules and dyanmically import"""

    def import_error(name: str) -> Exception | None:
        try:
            _ = importlib.import_module(name)
        except Exception as e:
            return e

    import_errors = {
        mod.name: mod_error
        for mod in _iter_modules()
        if (mod_error := import_error(mod.name)) is not None
    }

    assert not import_errors, f"Failed imports: {import_errors}"
