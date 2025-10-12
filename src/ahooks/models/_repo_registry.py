from __future__ import annotations

import importlib
import pkgutil
from functools import lru_cache
from typing import TYPE_CHECKING

from useful_types import SequenceNotStr as Sequence

if TYPE_CHECKING:
    from .repoConfigBlock import RepoConfigBlock


def _load_all_hooks() -> None:
    """Initialize and register all hooks in the package"""
    pkg = importlib.import_module("ahooks.hooks")
    for mod in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        importlib.import_module(mod.name)  # pyright: ignore[reportUnusedCallResult]


@lru_cache(maxsize=1)
def get_module_precommit_repo() -> RepoConfigBlock:
    """Use this loader for accessing the module precommit repo (besides for function registration)"""
    _load_all_hooks()
    from .repoConfigBlock import _module_precommit_repo

    return _module_precommit_repo
