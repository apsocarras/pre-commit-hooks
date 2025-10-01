"""Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks"""

from __future__ import annotations

from collections.abc import Collection
from typing import Callable, Literal, TypedDict, TypeVar

from typing_extensions import Any, NotRequired, ParamSpec, Unpack

GitStage = Literal["pre-commit", "pre-push"]
Language = Literal["system", "python"]

P = ParamSpec("P")
R = TypeVar("R")


class _PreCommitConfigYaml(TypedDict):
    """Schema for `.pre-commit-config.yaml` file"""

    repos: tuple[_RepoConfigBlock, ...]


class _RepoConfigBlock(TypedDict):
    """Repo entry in .pre-commit-config.yaml"""

    repo: str
    hooks: tuple[_HookBlockKwargs, ...]


class _HookBlockKwargs(TypedDict):
    id: str
    name: NotRequired[str | None]
    language: NotRequired[str | None]
    additional_dependencies: NotRequired[Collection[str] | None]
    entry: NotRequired[str | None]
    pass_filenames: NotRequired[bool | None]
    files: NotRequired[str | None]
    stages: NotRequired[Collection[GitStage] | None]
    args: NotRequired[Collection[str] | None]


class PreCommitConfigRepo:
    """Store any hook config blocks within the same repo via this container"""

    def __init__(self, repo: str = "local") -> None:
        self._repo: str = repo
        self._hooks: set[Callable[..., Any]] = set()

    def add_hook(self, h: Callable[..., Any]) -> None:
        self._hooks.add(h)

    def to_config(self) -> _PreCommitConfigYaml:
        """Dump to dict matching yaml schema"""
        _repo_config_block: _RepoConfigBlock = {
            "repo": self._repo,
            "hooks": tuple[_HookBlockKwargs, ...](
                hb.dump() for h in self._hooks if (hb := HookConfigBlock.extract(h))
            ),
        }
        return {"repos": (_repo_config_block,)}


_module_precommit_repo = PreCommitConfigRepo()


class HookConfigBlock:
    """Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks

    Corresponds to the `hook` level entries (under `hooks` in the yaml)
    """

    def __init__(
        self,
        repo: PreCommitConfigRepo = _module_precommit_repo,
        **kwargs: Unpack[_HookBlockKwargs],
    ) -> None:
        self._repo: PreCommitConfigRepo = repo
        self.id: str = kwargs["id"]
        self.name: str | None = kwargs.get("name")
        self.entry: str | None = kwargs.get("entry")
        self.language: str | None = kwargs.get("language")
        self.pass_filenames: bool | None = kwargs.get("pass_filenames")
        self.files: str | None = kwargs.get("files")
        self.stages: tuple[GitStage, ...] | None = (
            tuple(k) if (k := kwargs.get("stages")) is not None else None
        )
        self.args: tuple[str, ...] | None = (
            tuple(k) if (k := kwargs.get("args")) is not None else None
        )

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        """Attach or append to a hidden member `_pc_config: list[HookConfigBlock]` to a function

        Also registers the function in the repo block
        """
        if not hasattr(func, "_pc_config"):
            func._pc_config = [self]  # pyright: ignore[reportFunctionMemberAccess]
        else:
            func._pc_config.append(self)  # pyright: ignore[reportFunctionMemberAccess, reportAny]
        self._repo.add_hook(func)
        return func

    @classmethod
    def extract(cls, func: Callable[P, R]) -> HookConfigBlock | None:
        if isinstance((c := getattr(func, "_pc_config", None)), HookConfigBlock):
            return c
        return None

    def dump(self) -> _HookBlockKwargs:
        d: _HookBlockKwargs = {"id": self.id}
        for name, a in (
            ("name", self.name),
            ("entry", self.entry),
            ("language", self.language),
            ("pass_filenames", self.pass_filenames),
            ("files", self.files),
            ("stages", self.stages),
            ("args", self.args),
        ):
            if a is not None:
                d[name] = a
        return d
