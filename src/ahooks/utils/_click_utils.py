from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

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


def updated(hook_name: str, path: Path | str) -> None:
    click.echo(f"[{hook_name}] Updated and staged: {path}")


def stage_if_true(cond: bool, /, hook_name: str, path: Path) -> None:
    if cond:
        git_add(path)
        click.echo(f"[{hook_name}] Updated and staged: {path}")
    else:
        click.echo(f"[{hook_name}] Up to date: {path}")
