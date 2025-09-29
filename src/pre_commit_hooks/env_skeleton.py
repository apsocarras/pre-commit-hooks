import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import click

from pre_commit_hooks.utils._preCommitConfigBlock import PreCommitConfigBlock as cb
from pre_commit_hooks.utils.click_utils import (
    READ_DIR_TYPE,
    READ_FILE_TYPE,
    WRITE_FILE_TYPE,
)

from .utils.git_utils import check_ignored, find_repo_root


def warn_if_git_ignored(git_root: Path, skelenv_path: Path) -> None:
    """If the mock .env path would be ignored...there's no real point to this hook."""
    if check_ignored(git_root, skelenv_path):
        warnings.warn(f"{skelenv_path} is ignored.")


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
@click.argument("skelenv_path", type=WRITE_FILE_TYPE)
@cb(
    id="env-skeleton",
    name="Create an example `.env` file with only the names of variables",
    entry="python -m ahooks.env_skeleton",
    language="system",
    pass_filenames=False,
    args=(".", ".env", ".env.skeleton"),
    stages=("pre-commit", "pre-push"),
)
def main(git_repo_root: Path, base_env_path: Path, skelenv_path: Path) -> None:
    """Create an example `.env` file with only the names of variables.

    Keeps a Git-safe record of what .env vars you may set for the project.
    """
    git_root: Path = find_repo_root(git_repo_root)
    warn_if_git_ignored(git_root, skelenv_path)

    with skelenv_path.open("w") as file:

        def write_(d: Any) -> None:  # wrapper to placate pyright
            file.write(d)  # pyright: ignore[reportUnusedCallResult, reportAny]

        for var in iter_env_var_names(base_env_path):
            write_(var)
            write_("\n")


if __name__ == "__main__":
    main()
