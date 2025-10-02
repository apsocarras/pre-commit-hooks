"""Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks"""

from __future__ import annotations

from typing import Any, Callable

import attr
import cattrs
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn
from click.utils import P, R
from typing_extensions import Any

from ahooks._types import GitStage


@attr.define
class PreCommitConfigYaml:
    """Schema for `.pre-commit-config.yaml` file"""

    repos: list[RepoConfigBlock]


@attr.define
class RepoConfigBlock:
    """Repo entry in .pre-commit-config.yaml."""

    repo: str = attr.field(default="local")
    hooks: list[HookConfigBlock] = attr.field(factory=list)

    def add_hook(self, hook: HookConfigBlock):
        self.hooks.append(hook)


_module_precommit_repo = RepoConfigBlock()


@attr.define
class HookConfigBlock:
    """Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks.

    Corresponds to the `hook` level entries (under `hooks` in the yaml)
    """

    id: str = attr.field()
    name: str | None = attr.field(default=None)
    entry: str | None = attr.field(default=None)
    language: str | None = attr.field(default=None)
    pass_filenames: bool | None = attr.field(default=None)
    files: str | None = attr.field(default=None)
    stages: tuple[GitStage, ...] | None = attr.field(default=None)
    args: tuple[str, ...] | None = attr.field(default=None)

    _repo: RepoConfigBlock = attr.field(
        factory=lambda: _module_precommit_repo, metadata={"omit": True}
    )
    _funcs: set[Callable[..., Any]] = attr.field(
        factory=set, init=False, repr=False, metadata={"omit": True}
    )

    def __attrs_post_init__(self) -> None:
        """Registers self with the passed repo config block"""
        self._repo.add_hook(self)

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        """Registers the function with itself (and by extension its repo member)"""
        self._funcs.add(func)
        return func


conv = cattrs.Converter()

# JSON serialiization
conv.register_unstructure_hook(tuple, list)
conv.register_unstructure_hook(set, list)


def _omit_unstructurer(cls) -> Callable[..., dict[str, Any]]:
    """Omit if field metadata says to"""
    fn: Callable[[Any], dict[str, Any]] = make_dict_unstructure_fn(
        cls, conv, _cattrs_omit_if_default=True
    )

    def wrapped(inst) -> dict[str, Any]:
        d = fn(inst)
        return {
            k: v
            for k, v in d.items()
            if not getattr(cls.__attrs_attrs__[k].metadata, "get", lambda _: False)(
                "omit"
            )
        }

    return wrapped


for cls in (HookConfigBlock, RepoConfigBlock, PreCommitConfigYaml):
    conv.register_unstructure_hook(cls, _omit_unstructurer(cls))
    conv.register_structure_hook(cls, make_dict_structure_fn(cls, conv))
