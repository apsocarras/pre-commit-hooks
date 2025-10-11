"""Export all or any of the hooks in this package into a `pre-commit-config.yaml`"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path

import click
from ruamel.yaml import YAML
from useful_types import SequenceNotStr as Sequence

from ahooks.utils._click_utils import WRITE_FILE_TYPE
from ahooks.utils.preCommitConfigYaml import dump_ahook_config

from ._types import (
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
    # case_sensitive=False,
    multiple=True,
    help="Optionally specify which hooks in the package you want to export. If none provided, exports all hooks. Can be invoked multiple times.",
    show_choices=True,
    default=(),
)
@click.option(
    "-o",
    "config_path",
    type=WRITE_FILE_TYPE,
    help="Path to the to the pre-commit config. If it exists, the hooks will be inserted into it.",
    default=None,
)
@click.option(
    "-h",
    "hooks_only",
    is_flag=True,
    help="Whether to export the hook to a `.pre-commit-hooks.yaml` and exclude the config metadata",
    default=False,
)
def export(
    hooks: tuple[HookChoice, ...] = (),
    config_path: Path | None = None,
    hooks_only: bool = False,
) -> None:
    """Export the hooks in this package to a `pre-commit-config.yaml`

    Arguments:
        hooks : tupel[str, ...], default = (,)
        Optionally specify which hooks in the package you want to export. If none provided, exports all hooks.
        config_path : Path, default = Path.cwd() / ".pre-commit-config.yaml"
        Path to the to the pre-commit config. If it exists, the hooks will be inserted into it.

    """
    path_base: Callable[[Path], str] = (
        lambda p: re.sub("config", "hooks", p.name) if hooks_only else p.name
    )

    if config_path is not None:
        _res_path = config_path.parent / path_base(config_path)
    else:
        _res_path = Path.cwd() / (
            f".pre-commit-{'config' if not hooks_only else 'hooks'}.yaml"
        )

    if dump_ahook_config(_res_path, hooks_only, *hooks):
        click.echo(f"\nWrote hooks to {_res_path}")
    else:
        click.echo(
            f"\nAdded no hooks to {_res_path.name} (hook ids already present in config)"
        )


if __name__ == "__main__":
    export()
