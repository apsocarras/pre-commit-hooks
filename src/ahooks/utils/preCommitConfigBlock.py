"""Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks"""

from __future__ import annotations

from collections.abc import Collection
from typing import Callable, Literal, TypedDict, TypeVar

from typing_extensions import NotRequired, ParamSpec, Unpack

GitStage = Literal["pre-commit", "pre-push"]
Language = Literal["system", "python"]

P = ParamSpec("P")
R = TypeVar("R")


class _PcbArgs(TypedDict):
    id: str
    name: NotRequired[str | None]
    language: NotRequired[str | None]
    additional_dependencies: NotRequired[Collection[str] | None]
    entry: NotRequired[str | None]
    pass_filenames: NotRequired[bool | None]
    files: NotRequired[str | None]
    stages: NotRequired[Collection[GitStage] | None]
    args: NotRequired[Collection[str] | None]


class PreCommitConfigBlock:
    """Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks"""

    def __init__(self, **kwargs: Unpack[_PcbArgs]) -> None:
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
        """Attach or append to a hidden member `_pc_config: list[PreCommitConfigBlock]` to a function"""
        if not hasattr(func, "_pc_config"):
            func._pc_config = [self]  # pyright: ignore[reportFunctionMemberAccess]
        else:
            func._pc_config.append(self)  # pyright: ignore[reportFunctionMemberAccess, reportAny]
        return func
