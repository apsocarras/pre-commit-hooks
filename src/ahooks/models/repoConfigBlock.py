"""Model for an entry under the `repos` block in a `.pre-commit-config.yaml`"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Protocol, runtime_checkable

import attr
from typing_extensions import override
from useful_types import SequenceNotStr as Sequence

from .._types import GitStage
from ..utils._nobeartype import nobeartype

logger = logging.getLogger(__name__)


@runtime_checkable
class HookConfigBlockProto(Protocol):
    """Placeholder for RepoConfigBlock"""

    id: str = attr.field()
    name: str | None = attr.field(default=None)
    language: str | None = attr.field(default=None)
    entry: str | None = attr.field(default=None)
    args: tuple[str, ...] | None = attr.field(default=None)
    pass_filenames: bool | None = attr.field(default=None)
    files: str | None = attr.field(default=None)
    stages: tuple[GitStage, ...] | None = attr.field(default=None)
    _repo: RepoConfigBlock
    _funcs: set[Callable[..., Any]]


@attr.define
class RepoConfigBlock:
    """Repo entry in .pre-commit-config.yaml."""

    repo: str
    hooks: list[HookConfigBlockProto] = attr.field(factory=list)

    @nobeartype
    def add_hook(self, hook: HookConfigBlockProto, guard: bool = False) -> None:
        """Append a hook to the end of the hook list"""
        if guard and self.has_hook(hook):
            return
        self.hooks.append(hook)

    @nobeartype
    def has_hook(self, hook: HookConfigBlockProto) -> bool:
        """Checks if a hook of the same id is already in the hook list"""
        has_ = any(h.id == hook.id for h in self.hooks)
        logger.debug(msg=tuple(h.id for h in self.hooks))
        return has_

    @override
    def __eq__(self, o: object, /) -> bool:
        if not isinstance(o, RepoConfigBlock) or not len(o.hooks) == len(self.hooks):
            return False
        _s = sorted(self.hooks, key=lambda h: h.id)
        _o = sorted(o.hooks, key=lambda h: h.id)
        return all(s == o for s, o in zip(_s, _o, strict=False))


## Use this singleton in the bodies of HookConfigBlock to register function hooks in module
_module_precommit_repo = RepoConfigBlock(repo="local")
## Besides that, use the get_precommit_repo loader if you need to access it


def _load_all_hooks() -> None:
    """Initialize and register all hooks in the package"""
    pkg = importlib.import_module("ahooks.hooks")
    for mod in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        importlib.import_module(mod.name)  # pyright: ignore[reportUnusedCallResult]


@lru_cache(maxsize=1)
def get_module_precommit_repo() -> RepoConfigBlock:
    """Use this loader for accessing the module precommit repo (besides for function registration)"""
    _load_all_hooks()
    return _module_precommit_repo
