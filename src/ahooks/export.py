"""Export all or any of the hooks in this package into a `pre-commit-config.yaml`"""

from __future__ import annotations

import enum
import io
from pathlib import Path
from random import choice
from re import match
from typing import Any, Callable
import warnings

import click
from typing_extensions import Sentinel

from ._types import FAILED_OP, FINISH_OP, OMITTED_DEFAULT, FailedOpSentinel, HookChoice, OpSentinel
from ahooks._exceptions import PreCommitYamlValidationError
from ahooks.utils._click_utils import WRITE_FILE_TYPE
from ahooks.utils.preCommitConfigYaml import PreCommitConfigYaml, HookConfigBlock, RepoConfigBlock, conv

from .utils._file_utils import write_, write_atomic, write_if_changed
from ruamel.yaml import YAML 
import logging


logger = logging.getLogger(__name__)


yaml = YAML()


# fmt: off
_MODULE_CHOICES: tuple[HookChoice, ...] = (
    "add-from-future",
    "env-skeleton",
    "emit-requirements"
)
# fmt: on


def _get_config_yaml(*hook_choices: HookChoice) -> PreCommitConfigYaml:
    from .utils.preCommitConfigYaml import (
        _module_precommit_repo,  # pyright: ignore [reportPrivateUsage]
    )

    if hook_choices:
        choice_set = set(hook_choices)
        filtered_hooks = [h for h in _module_precommit_repo.hooks if h in choice_set]
        filtered_repo = RepoConfigBlock(hooks=filtered_hooks)
        return PreCommitConfigYaml(repos=[filtered_repo])
    else:
        return PreCommitConfigYaml(repos=[_module_precommit_repo])

def _write_config(path: Path, config_data: dict[str, Any]) -> None: 
    buf = io.StringIO()
    yaml.dump(config_data, buf)
    write_atomic(path, buf.getvalue())


def _append_hooks_to_repo_block(repo_name: str, path: Path, *hooks) -> OpSentinel:
    try: 
        # Locate insertion point
        with path.open("r") as file: 
            config= yaml.load_all(file)
        matches_name = lambda r: r['repo'].strip().lower() == repo_name
        idx = next(n for n, r in enumerate(config['repos']) if matches_name(r))
    except StopIteration:
        return FAILED_OP
    try: 
        # Append hooks
        exist_hooks = config['repos'][idx]['repo']['hooks']
        exist_hook_ids = set(h['id'] for h in exist_hooks)
        added = False
        for h in hooks:
            if h['id'] in exist_hook_ids:
                warnings.warn(f"Provided yaml {path.name} already has a hook named {h['id']}. Skipping.")
                continue
            config.append(h)
            added = True
        if not added:
            logger.info(f"No new hooks provided -- not writing to {path.name}")
        else: 
            buf = io.StringIO()
            yaml.dump(config, buf)
            write_atomic(path, buf.getvalue())

        return FINISH_OP
    except (KeyError, TypeError) as e:
        raise PreCommitYamlValidationError(path) from e

def _dump_yaml(path: Path):
    data = _get_config_yaml()
    if not path.exists(): 
        with path.open("w") as file:
            yaml.dump(data, file)
        return FINISH_OP

    with path.open("r") as file: 
        existing_config= yaml.load_all(file)

    repo = data["repos"][0]
    repo_name, hooks = repo['repo'], repo['hooks']
    append_result= _append_hooks_to_repo_block(repo_name, path, hooks)

    if append_result: 
        return FINISH_OP
    
    existing_config['repos'].append(repo)
    write_atomic(path, (existing_config))
      
    
    idx = _insert_idx()
    if idx != -1:
        existing_config['repos'][idx]['repo']['hooks']



x = [1,2,3]
b = next(n for n, y in enumerate(x) if False)

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
    hooks: tuple[str, ...] = (),
    config_path: Path | Sentinel = OMITTED_DEFAULT,
):
    """Export the hooks in this package to a `pre-commit-config.yaml`

    Arguments:
        hook : tupel[str, ...], default = (,)
        Optionally specify which hooks in the package you want to export. If none provided, exports all hooks.
        config_path : Path, default = Path.cwd() / ".pre-commit-config.yaml"
        Path to the to the pre-commit config. If it exists, the hooks will be inserted into it.

    """
    _res_path: Path = (
        Path.cwd() / ".pre-commit-config.yaml"
        if isinstance(config_path, Sentinel)
        else config_path
    )

    if _res_path.exists()
