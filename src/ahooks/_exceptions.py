from __future__ import annotations

import textwrap
from collections.abc import Callable
from functools import wraps
from typing import Protocol, TypeVar, runtime_checkable

from typing_extensions import Concatenate, ParamSpec

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")


class AnalyzerException(Exception):
    pass


@runtime_checkable
class HasLinePosition(Protocol):
    @property
    def lineno(self) -> int: ...
    @property
    def col_offset(self) -> int: ...


class AnalyzerVisitException(AnalyzerException):
    """Lifted from tryceratops

    https://github.com/guilatrova/tryceratops/blob/56dbdf83ac0202d94e68877fac0a17c20c0a4c4f/src/tryceratops/analyzers/exceptions.py
    """

    def __init__(self, node: HasLinePosition):
        self.node = node
        super().__init__(
            textwrap.dedent(f"""
            Unexpected error when analyzing '{type(node).__name__}' statement at
            {node.lineno}:{node.col_offset}
            """)
        )


def visit_error_handler(
    func: Callable[Concatenate[T, P], R],
) -> Callable[Concatenate[T, P], R]:
    @wraps(func)
    def wrapper(self: T, *args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            node = kwargs.get("node", args[0] if args else None)
            if isinstance(node, HasLinePosition):
                raise AnalyzerVisitException(node) from e
            raise

    return wrapper


class SequenceStrViolation(Exception):
    def __init__(self, node: HasLinePosition) -> None:
        self.node: HasLinePosition = node
        super().__init__(
            textwrap.dedent(f"""
            Bare `Sequence[str]` detected! {node.lineno}:{node.col_offset}
            """)
        )
