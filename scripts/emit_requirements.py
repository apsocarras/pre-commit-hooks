"""
Emit `requirements.txt` from a `pyproject.toml` using `uv`

If the `pyproject.toml` has a `test` group, it includes it.
    - The only real purpose of emitting requirements.txt is for
    cloud deployment, which is usually in CI/CD pipelines.
"""

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

logger = logging.getLogger(__name__)


class TestDepsType(Enum):
    GROUP = "group"
    EXTRA = "extra"


def get_dep_type(
    toml_file: Path,
) -> Literal[TestDepsType.GROUP, TestDepsType.EXTRA] | None:
    toml: dict[str, Any] = tomli.loads(toml_file.read_text("utf-8"))
    groups = toml.get("dependency-groups", {})
    if "test" in groups:
        return TestDepsType.GROUP
    project = toml.get("project", {})
    opt = project.get("optional-dependencies", {})
    if "test" in opt:
        return TestDepsType.EXTRA
    return None


def construct_command(dep_type: TestDepsType | None) -> list[str]:
    cmd = ["uv", "pip", "compile"]
    if dep_type == TestDepsType.GROUP:
        cmd += ["--group", "test"]
    elif dep_type == TestDepsType.EXTRA:
        cmd += ["--extra", "test"]
    cmd += ["pyproject.toml", "-o", "requirements.txt"]
    return cmd


@click.command
def main():
    if not shutil.which("uv"):
        warnings.warn("You must install `uv` to run this hook.")
        sys.exit(1)
    if not (path := Path("pyproject.toml")).is_file():
        warnings.warn("`uv pip compile` requires a pyproject.toml in the project root.")
        sys.exit(1)

    dep_type = get_dep_type(path)
    cmd = construct_command(dep_type)
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
