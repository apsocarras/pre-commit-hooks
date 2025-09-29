from __future__ import annotations

from collections.abc import Collection
from functools import wraps  # noqa
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
    """
    Use for applying default configs to the hooks.
    """

    def __init__(self, **kwargs: Unpack[_PcbArgs]) -> None:
        self.id: str = kwargs["id"]
        self.name: str | None = kwargs.get("name", None)
        self.entry: str | None = kwargs.get("entry", None)
        self.language: str | None = kwargs.get("language", None)
        self.pass_filenames: bool | None = kwargs.get("pass_filenames", None)
        self.files: str | None = kwargs.get("files", None)
        self.stages: tuple[GitStage, ...] | None = (
            tuple(k) if (k := kwargs.get("stages", None)) is not None else None
        )
        self.args: tuple[str, ...] | None = (
            tuple(k) if (k := kwargs.get("args", None)) is not None else None
        )

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        if not hasattr(func, "_pc_config"):
            setattr(func, "_pc_config", [self])
        else:
            func._pc_config.append(self)  # pyright: ignore[reportFunctionMemberAccess, reportAny]
        return func
