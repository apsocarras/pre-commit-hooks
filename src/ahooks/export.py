"""Export all or any of the hooks in this package into a `pre-commit-config.yaml`"""

from __future__ import annotations

import logging
from pathlib import Path

import click
from ruamel.yaml import YAML
from typing_extensions import Sentinel
from useful_types import SequenceNotStr as Sequence

from ahooks.utils._click_utils import WRITE_FILE_TYPE
from ahooks.utils.preCommitConfigYaml import dump_ahook_config

from ._types import (
    OMITTED_DEFAULT,
    HookChoice,
)

logger = logging.getLogger(__name__)


yaml = YAML()


# fmt: off
_MODULE_CHOICES: tuple[HookChoice, ...] = (
    "add-from-future",
    "env-skeleton",
    "emit-requirements"
)
# fmt: on


@click.command
# @click.option(
#     "module",
#     "-mod",
#     help=textwrap.dedent("""
#     TODO: The name of the .py module from which you want to export hooks.
#     Will add this option to expand the use of this script and the registration decorators
#     beyond the use of just this package.
#     """),
# )
@click.option(
    "-k",
    "hooks",
    type=click.Choice(_MODULE_CHOICES),
    case_sensitive=False,
    multiple=True,
    help="Optionally specify which hooks in the package you want to export. If none provided, exports all hooks. Can be invoked multiple times.",
    show_choices=True,
)
@click.option(
    "-o",
    "config_path",
    type=WRITE_FILE_TYPE,
    help="Path to the to the pre-commit config. If it exists, the hooks will be inserted into it.",
)
def export(
    hooks: tuple[HookChoice, ...] = (),
    config_path: Path | Sentinel = OMITTED_DEFAULT,
):
    """Export the hooks in this package to a `pre-commit-config.yaml`

    Arguments:
        hooks : tupel[str, ...], default = (,)
        Optionally specify which hooks in the package you want to export. If none provided, exports all hooks.
        config_path : Path, default = Path.cwd() / ".pre-commit-config.yaml"
        Path to the to the pre-commit config. If it exists, the hooks will be inserted into it.

    """
    _res_path: Path = (
        Path.cwd() / ".pre-commit-config.yaml"
        if isinstance(config_path, Sentinel)
        else config_path
    )

    if dump_ahook_config(_res_path, *hooks):
        click.echo(f"Wrote hooks to {_res_path}")
    else:
        click.echo(
            f"Added no hooks to {_res_path} (hook ids already present in config.)"
        )
