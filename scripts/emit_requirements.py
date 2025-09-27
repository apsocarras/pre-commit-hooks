"""
Emit `requirements.txt` from a `pyproject.toml` using `uv`.
If the `pyproject.toml` has a `test` group, it includes it.
    - The main purpose of emitting requirements.txt is for
    remote deployment, usually in CI/CD pipelines, where
    requirements.txt is used.
"""

import logging
from pathlib import Path
import shutil
import subprocess
import click
import tomli 
import os 

logger = logging.getLogger(__name__)


def parse_pyproject_toml(path: Path): 

@click.command
@click.argument("")
def main():
    if not shutil.which("uv"):
        logger.debug("Install `uv` to run this hook.")
        return

    

    subprocess.run(
        [
            "uv",
            "pip",
            "compile",
            "--group",
            "test",
        ]
    )


if __name__ == "__main__":
    main()
