"""
Create an example `.env` file which includes only the names of
the variables therein. Keeps a .git-safe record of what .env vars
you may set for the project.
"""

import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import click

from .utils.git_utils import check_ignored, find_repo_root

READ_DIR_TYPE = click.Path(
    exists=True, file_okay=False, dir_okay=True, path_type=Path, readable=True
)

READ_FILE_TYPE = click.Path(
    exists=True, file_okay=True, dir_okay=False, path_type=Path, readable=True
)
WRITE_FILE_TYPE = click.Path(
    exists=False, file_okay=True, dir_okay=False, path_type=Path, writable=True
)


def warn_if_git_ignored(git_root: Path, mock_env_path: Path) -> None:
    """
    If the mock .env path would be ignored...there's no real point to this hook.
    """
    if check_ignored(git_root, path=mock_env_path):
        warnings.warn(f"{mock_env_path} is ignored.")


def iter_env_var_names(p: Path, include_eq_sign: bool = True) -> Iterable[str]:
    offset = 0 if not include_eq_sign else 1
    for l in p.read_text().splitlines():
        if not (ls := l.strip()) or ls.startswith("#"):
            continue
        if (idx := l.find("=")) == -1:
            continue
        yield l[: idx + offset]


@click.command
@click.argument("git_repo_root", type=READ_DIR_TYPE)
@click.argument("base_env_path", type=READ_FILE_TYPE)
@click.argument("mock_env_path", type=WRITE_FILE_TYPE)
def main(git_repo_root: Path, base_env_path: Path, mock_env_path: Path) -> None:
    git_root: Path = find_repo_root(git_repo_root)
    warn_if_git_ignored(git_root, mock_env_path)

    with mock_env_path.open("w") as file:

        def write_(d: Any) -> None:  # wrapper to placate pyright
            file.write(d)  # pyright: ignore[reportUnusedCallResult, reportAny]

        for var in iter_env_var_names(base_env_path):
            write_(var)
            write_("\n")
