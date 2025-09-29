"""Throw an error if any `.py file` contains a `Sequence[str]` (barring `Sequence[str] | str`)

* `Sequence[str] | str` is fine (explicitly allows `str`)
* `Sequence[str]` alone is banned (implicitly allows `str`)

See the following for implementations of a true `SequenceNotStr[str]`:
* https://github.com/python/typing/issues/256#issuecomment-1442633430
* https://github.com/hauntsaninja/useful_types/blob/main/useful_types/__init__.py

"""

from __future__ import annotations

import click

from .utils import PreCommitConfigBlock as cb


@click.command
@cb(
    id="sequence-not-str",
    name="Throw an error if any `.py file` contains a `Sequence[str]` (barring `Sequence[str] | str`)",
    language="python",
    entry="python -m ahooks.sequence_not_str",
    pass_filenames=True,
    stages=["pre-commit", "pre-push"],
    files=r"^.*\.py$",
)
def main():
    ...
    ## TODO:
    # attempt to import the provided protocol path
    # confirm it matches the spec
    # traverse the ast of each provided .py files
    # replace all usages of
