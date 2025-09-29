from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import click
import tomli

from .utils import PreCommitConfigBlock as cb

logger = logging.getLogger(__name__)


class _TestDepsType(Enum):
    GROUP = "group"
    EXTRA = "extra"


def _get_dep_type(
    toml_file: Path,
) -> Literal[_TestDepsType.GROUP, _TestDepsType.EXTRA] | None:
    toml: dict[str, Any] = tomli.loads(toml_file.read_text("utf-8"))
    groups = toml.get("dependency-groups", {})
    if "test" in groups:
        return _TestDepsType.GROUP
    project = toml.get("project", {})
    opt = project.get("optional-dependencies", {})
    if "test" in opt:
        return _TestDepsType.EXTRA
    return None


def _construct_command(dep_type: _TestDepsType | None) -> list[str]:
    cmd = ["uv", "pip", "compile"]
    if dep_type == _TestDepsType.GROUP:
        cmd += ["--group", "test"]
    elif dep_type == _TestDepsType.EXTRA:
        cmd += ["--extra", "test"]
    cmd += ["pyproject.toml", "-o", "requirements.txt"]
    return cmd


@click.command
@cb(
    id="block-manual-req-edits",
    name="Block manual edits to requirements.txt",
    ## TODO: Ideally, for portability reasons, I would provide another script in this python package
    # to handle this pre-filter. But anyone can modify the default pre-config blocks after they're output.
    entry=r"""
     bash -c
            if git diff --cached --name-only | grep -q "^requirements\.txt$" &&
                ! git diff --cached --name-only | grep -q "^pyproject\.toml$"; then
                echo "Edit pyproject.toml and run the emitter; don't hand-edit requirements.txt."
                exit 1
            fi
    """,
    language="system",
    pass_filenames=False,
    files=r"^requirements\.txt$",
    stages=("pre-commit", "pre-push"),
)
@cb(
    id="emit-requirements",
    name="Emit requirements.txt from pyproject.toml using `uv`",
    entry="python -m ahooks.emit_requirements",
    language="system",
    pass_filenames=False,
    files=r"^(pyproject\.toml|requirements\.txt)$",
    stages=("pre-commit", "pre-push"),
)
def main():
    """
    Emit `requirements.txt` from a `pyproject.toml` using `uv`

    If the `pyproject.toml` has a `test` group, it includes it.
        - The only real purpose of emitting requirements.txt is for
        cloud deployment, which is usually in CI/CD pipelines.
    """
    if not shutil.which("uv"):
        warnings.warn("You must install `uv` to run this hook.", stacklevel=2)
        sys.exit(1)
    if not (path := Path("pyproject.toml")).is_file():
        warnings.warn(
            "`uv pip compile` requires a pyproject.toml in the project root.",
            stacklevel=2,
        )
        sys.exit(1)

    dep_type = _get_dep_type(path)
    cmd = _construct_command(dep_type)
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.log(
        (logging.ERROR if result.returncode != 0 else logging.DEBUG),
        {
            "event": "emit-requirements",
            "details": {"stderr": result.stderr.strip(), "stdout": result.stdout},
        },
    )
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
