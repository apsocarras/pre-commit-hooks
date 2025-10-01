# from __future__ import annotations
from __future__ import annotations

import ast
import textwrap
from collections.abc import Callable

import mypy  # noqa
from mypy.plugin import AnalyzeTypeContext, Plugin
from mypy.types import Type
from typing_extensions import override


class CustomPlugin(Plugin):
    @override
    def get_type_analyze_hook(
        self, fullname: str
    ) -> Callable[[AnalyzeTypeContext], Type] | None:
        return super().get_type_analyze_hook(fullname)


arr = []
arr[0]: int = 1
src = "arr[0]: int = 1"
tree = ast.parse(src, mode="eval")


def main():
    mock_py_file = textwrap.dedent("""
    from collections.abc import Sequence
    from typing import Annotated, TypeAlias, TypeVar
    import typing as t

    foo: Sequence[str] | str = ("foo",)

    A: TypeAlias = Sequence[str] | str
    B: TypeAlias = Sequence[str]
    C = TypeVar("C", Sequence[str], object)

    class Foo(object):
        pass

    f = Foo()
    f.x: Sequence[str]
    d = {}
    d['foo']: Sequence[str] = 'bar'


    """)

    ast_mod = ast.parse(
        mock_py_file,
    )

    for node in ast_mod.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        print(ast.dump(node, indent=4))


if __name__ == "__main__":
    main()
