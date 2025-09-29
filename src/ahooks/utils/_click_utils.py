from __future__ import annotations

from pathlib import Path

import click

from ahooks.utils.git_utils import git_add

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


def stage_if_true(cond: bool, /, hook_name: str, path: Path):
    if cond:
        git_add(path)
        click.echo(f"[{hook_name}] Updated and staged: {path}")
    else:
        click.echo(f"[{hook_name}] Up to date: {path}")
