"""Model for an entry under the `hooks` block in a `.pre-commit-config.yaml`"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import attr
from typing_extensions import override
from useful_types import SequenceNotStr as Sequence

from .._types import (
    GitStage,
    P,
    R,
)
from ..utils._nobeartype import nobeartype

if TYPE_CHECKING:
    from .repoConfigBlock import RepoConfigBlock


logger = logging.getLogger(__name__)


@nobeartype
def _module_precommit_repo_factory() -> RepoConfigBlock:
    """Deferring import to avoid circle"""
    from .repoConfigBlock import _module_precommit_repo

    return _module_precommit_repo


@runtime_checkable
class RepoConfigBlockProto(Protocol):
    """Placeholder for RepoConfigBlock"""

    def add_hook(self, *args, **kwargs) -> None: ...  # type: ignore[no-untyped-def] # noqa: D102


@attr.define
class HookConfigBlock:
    """Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks.

    Corresponds to the `hook` level entries (under `hooks` in the yaml)
    """

    id: str = attr.field()
    name: str | None = attr.field(default=None)
    language: str | None = attr.field(default=None)
    entry: str | None = attr.field(default=None)
    args: tuple[str, ...] | None = attr.field(default=None)
    pass_filenames: bool | None = attr.field(default=None)
    files: str | None = attr.field(default=None)
    stages: tuple[GitStage, ...] | None = attr.field(default=None)

    _repo: RepoConfigBlockProto = attr.field(
        factory=lambda: _module_precommit_repo_factory(),
        metadata={"omit": True},
        alias="_repo",
    )
    _funcs: set[Callable[..., Any]] = attr.field(
        factory=set, init=False, repr=False, metadata={"omit": True}
    )

    def __attrs_post_init__(self) -> None:
        """Registers self with the passed repo config block"""
        self._repo.add_hook(self, guard=True)

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        """Registers the function with itself (and by extension its repo member)"""
        self._funcs.add(func)
        return func

    @override
    def __eq__(self, o: object, /) -> bool:
        """Only compares id parameter (for my purposes this is sufficient)"""
        return isinstance(o, HookConfigBlock) and o.id == self.id
