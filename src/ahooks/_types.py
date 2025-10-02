from __future__ import annotations

from collections.abc import Collection
from typing import Literal, NamedTuple, TypeVar, Union

from typing_extensions import NotRequired, ParamSpec, Sentinel, TypeAlias, TypedDict

GitStage = Literal["pre-commit", "pre-push"]
Language = Literal["system", "python"]

P = ParamSpec("P")
R = TypeVar("R")


class NodeLoc(NamedTuple):
    """Location of a node within a module"""

    idx: int
    lineno: int


HookChoice: TypeAlias = Union[
    Literal["add-from-future"], Literal["env-skeleton"], Literal["emit-requirements"]
]


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


OpSentinel: TypeAlias = Union[CompletedOpSentinel, FailedOpSentinel]


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
