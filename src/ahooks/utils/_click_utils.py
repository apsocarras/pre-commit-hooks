from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable

import click

from ahooks.utils.git_utils import git_add


class NotInstalledException(click.ClickException):
    def __init__(self, *args: str) -> None:
        super().__init__(
            f"You must install the following to use this hook: {', '.join(args)}."
        )


class SubprocessReturnCodeException(click.ClickException):
    def __init__(
        self,
        command_name: str,
        subprocess: CompletedProcess[str],
    ) -> None:
        super().__init__(
            f"`{command_name}` failed with exit code {subprocess.returncode}."
        )


def raise_if_return_code(command_name: str, result: CompletedProcess[str]) -> None:
    if result.returncode != 0:
        raise SubprocessReturnCodeException(command_name, result)


READ_DIR_TYPE = click.Path(
    exists=True, file_okay=False, dir_okay=True, path_type=Path, readable=True
)

READ_FILE_TYPE = click.Path(
    exists=True, file_okay=True, dir_okay=False, path_type=Path, readable=True
)
WRITE_FILE_TYPE = click.Path(
    exists=False, file_okay=True, dir_okay=False, path_type=Path, writable=True
)

WRITE_DIR_TYPE = click.Path(
    exists=True, file_okay=False, dir_okay=True, path_type=Path, writable=True
)


def echo_updated(hook_name: str, path: Path | str) -> None:
    click.echo(f"[{hook_name}] Updated: {path}")


def _hook_name(s: str) -> str:
    return f"[[{s.replace('_', '-')}]"


def _stage_msg(hook_name: str, *paths: Path | str):
    return f"{_hook_name(hook_name)} Updated and staged: {', '.join(str(p) for p in paths)}"


def stage_if_true(
    cond: bool,
    /,
    hook_name: str,
    stage_msg: Callable[[str, Path | str], str] = _stage_msg,
    *paths: Path,
) -> None:
    if cond:
        git_add(*paths)
        click.echo(stage_msg(hook_name, *paths))
    else:
        click.echo(f"[{hook_name}] All up to date")
