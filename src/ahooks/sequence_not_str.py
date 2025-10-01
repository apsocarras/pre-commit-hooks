"""Throw an error if any `.py file` contains a `Sequence[str]` (barring `Sequence[str] | str`)

* `Sequence[str] | str` is fine (explicitly allows `str`)
* `Sequence[str]` alone is banned (implicitly allows `str`)

See the following for implementations of a true `SequenceNotStr[str]`:
* https://github.com/python/typing/issues/256#issuecomment-1442633430
* https://github.com/hauntsaninja/useful_types/blob/main/useful_types/__init__.py

"""

from __future__ import annotations

import ast
from pathlib import Path

import click
from typing_extensions import override

from ahooks._exceptions import visit_error_handler
from ahooks._types import NodeLoc

from .utils import PreCommitConfigBlock as cb
from .utils._click_utils import READ_FILE_TYPE


class SequencePolice(ast.NodeVisitor):
    """
    *Officer to dispatch, we've got a 10-33*

    Tracks all annotation sites in a module to later expose and resolve any underlying `Sequence[str]`
    """

    @override
    def __init__(self, *args, **kwargs) -> None:
        self._annotation_sites: dict[str, NodeLoc] = {}
        super().__init__(*args, **kwargs)

    @override
    @visit_error_handler
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        def _get_target_name():
            if isinstance(node.target, ast.Name):
                return node.tr

        node.target.id
        self.generic_visit(node)

    @override
    @visit_error_handler
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.generic_visit(node)

    @override
    @visit_error_handler
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.generic_visit(node)

    @override
    @visit_error_handler
    def visit_withitem(self, node: ast.withitem) -> None:
        self.generic_visit(node)


@click.command
@click.argument("files", nargs=-1, type=READ_FILE_TYPE)
@cb(
    id="sequence-not-str",
    name="Throw an error if any `.py file` contains a `Sequence[str]` (barring `Sequence[str] | str`)",
    language="python",
    entry="python -m ahooks.sequence_not_str",
    pass_filenames=True,
    stages=["pre-commit", "pre-push"],
    files=r"^.*\.py$",
)
def main(files: tuple[Path, ...]) -> None:
    for f in files:
        src_code = f.read_text(encoding="utf-8")
        mod = ast.parse(src_code, filename=str(f))
        iter_sequence_str(mod)

    ## TODO:
    # attempt to import the provided protocol path
    # confirm it matches the spec
    # traverse the ast of each provided .py files
    # replace all usages of


if __name__ == "__main__":
    main()
