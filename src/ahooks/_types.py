from __future__ import annotations

import typing
from collections.abc import Collection, Iterable
from typing import (
    Literal,
    NamedTuple,
    TypeAlias,
    TypeVar,
    Union,
)

from typing_extensions import NotRequired, ParamSpec, Sentinel, TypedDict
from useful_types import SequenceNotStr as Sequence

_DeprecatedStages: TypeAlias = Literal["commit", "push"]
_Stages = Literal["pre-commit", "pre-push"]
GitStage = Literal["pre-commit", "pre-push", "commit", "push"]
Language = Literal["system", "python"]

P = ParamSpec("P")
R = TypeVar("R")


class NodeLoc(NamedTuple):
    """Location of a node within a module"""

    idx: int
    lineno: int


HookChoice: TypeAlias = Union[
    Literal["add-from-future"],
    Literal["allow-unused-required-imports"],
    Literal["env-skeleton"],
    Literal["emit-requirements"],
    Literal["block-manual-req-edits"],
]


def iter_hook_choices() -> Iterable[HookChoice]:
    for lit in typing.get_args(HookChoice):
        yield typing.get_args(lit)[0]


class FalseySentinel(Sentinel):
    def __bool__(self) -> Literal[False]:
        return False


class TruthySentinel(Sentinel):
    def __bool__(self) -> Literal[True]:
        return True


class OmittedDefaultSentinel(FalseySentinel):
    pass


class FailedOpSentinel(FalseySentinel):
    pass


class CompletedOpSentinel(TruthySentinel):
    pass


OMITTED_DEFAULT = OmittedDefaultSentinel("OMITTED_DEFAULT")

FAILED_OP = FailedOpSentinel("FAILED_OP")
FINISH_OP = CompletedOpSentinel("FINISH_OP")


OpSentinel: TypeAlias = CompletedOpSentinel | FailedOpSentinel


class HookBlockKwargs(TypedDict):
    id: str | HookChoice
    name: NotRequired[str | None]
    language: NotRequired[str | None]
    additional_dependencies: NotRequired[Collection[str] | None]
    entry: NotRequired[str | None]
    pass_filenames: NotRequired[bool | None]
    files: NotRequired[str | None]
    stages: NotRequired[Collection[GitStage] | None]
    args: NotRequired[Collection[str] | None]
