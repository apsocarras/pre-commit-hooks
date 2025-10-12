"""Destructure/restructure models, including file i/o"""

from __future__ import annotations

import io
import logging
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import Annotated, Any

import attr
import attrs
import cattrs
from cattrs.converters import Converter
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn
from useful_types import SequenceNotStr as Sequence

from ahooks._exceptions import PreCommitYamlValidationError
from ahooks._types import FAILED_OP, FINISH_OP, HookChoice, OpSentinel

from ..utils._file_utils import write_atomic
from ..utils._nobeartype import nobeartype
from ..utils._yaml import yaml
from .hookConfigBlock import HookConfigBlock
from .preCommitConfigYaml import PreCommitConfigYaml
from .repoConfigBlock import RepoConfigBlock, get_module_precommit_repo

logger = logging.getLogger(__name__)


def _omit_unstructurer(
    cls: type,
    conv: cattrs.Converter,
) -> Callable[..., dict[str, Any]]:
    """Omit if field metadata says to"""
    fn: Callable[[Any], dict[str, Any]] = make_dict_unstructure_fn(
        cls,
        conv,  # _cattrs_omit_if_default=omit_if_default # using custom metadata override
        _cattrs_omit_if_default=True,
    )

    @nobeartype
    def wrapped(
        inst: Annotated[
            attrs.AttrsInstance,
            "`attrs.AttrsInstance` is an empty protocol and not a real runtime type.",
        ],
    ) -> dict[str, Any]:
        d = fn(inst)
        return {
            k: v
            for k, v in d.items()
            if attr.has(cls_ := inst.__class__)
            and not attr.fields_dict(cls_)[k].metadata.get("omit", False)
        }

    return wrapped


def _register_hooks(conv: cattrs.Converter) -> None:
    # JSON serialiization
    conv.register_unstructure_hook(tuple, list)
    conv.register_unstructure_hook(set, list)

    for cls in (HookConfigBlock, RepoConfigBlock, PreCommitConfigYaml):
        conv.register_unstructure_hook(cls, _omit_unstructurer(cls, conv))
        conv.register_structure_hook(cls, make_dict_structure_fn(cls, conv))


def _get_converter() -> Converter:
    conv = cattrs.Converter()
    _register_hooks(conv)
    return conv


conv = _get_converter()


def dump_config(config: PreCommitConfigYaml, path: Path, hooks_only: bool) -> None:
    """Dump to yaml"""
    des = conv.unstructure(config)

    if hooks_only:
        d = des["repos"][0]["hooks"]
    else:
        d = (
            {
                "minimum_pre_commit_version": des["minimum_pre_commit_version"],
                "repos": des["repos"],
            }
            if "minimum_pre_commit_version" in des
            else des
        )
    buf: StringIO = io.StringIO()
    yaml.dump(d, buf)
    write_atomic(path, buf.getvalue())


def load_config(path: Path) -> PreCommitConfigYaml:
    """Load a .pre-commit-config.yaml into a structured object"""
    try:
        with path.open("r") as file:
            config = yaml.load(file)
        return conv.structure(config, PreCommitConfigYaml)
    except cattrs.BaseValidationError as e:
        raise PreCommitYamlValidationError() from e


def load_hooks(path: Path) -> list[HookConfigBlock]:
    """Load a .pre-commit-hooks.yaml as a list of hooks"""
    try:
        with path.open("r") as file:
            hooks = yaml.load(file)
        x: list[HookConfigBlock] = conv.structure(hooks, list[HookConfigBlock])
        return x
    except cattrs.BaseValidationError as e:
        raise PreCommitYamlValidationError() from e
    except Exception:
        raise


def get_ahook_config(*hook_choices: HookChoice) -> PreCommitConfigYaml:
    """Create a config yaml from this package's hooks"""
    _module_precommit_repo = get_module_precommit_repo()
    if hook_choices:
        choice_set = set(hook_choices)
        filtered_hooks = [h for h in _module_precommit_repo.hooks if h.id in choice_set]
        filtered_repo = RepoConfigBlock(repo="local", hooks=filtered_hooks)
        return PreCommitConfigYaml(repos=[filtered_repo])
    else:
        pc = PreCommitConfigYaml(repos=[_module_precommit_repo])
        return pc


def dump_ahook_config(
    path: Path, hooks_only: bool = False, *hooks: HookChoice
) -> OpSentinel:
    """Open the config yaml and append the packages's hooks (if the file exists) or create a new config.yaml"""
    module_config: PreCommitConfigYaml = get_ahook_config(*hooks)

    if not path.exists():
        dump_config(module_config, path, hooks_only)
        return FINISH_OP

    if not hooks_only:
        user_config: PreCommitConfigYaml = load_config(path)
    else:
        # lazily reusing same functions by wrapping hooks inside config yaml
        user_hooks = load_hooks(path)
        user_repo = RepoConfigBlock("local", user_hooks)
        user_config = PreCommitConfigYaml(repos=[user_repo])

    append_result: OpSentinel = user_config.extend(repo_block=module_config.repos[0])

    if not append_result:
        return FAILED_OP
    else:
        dump_config(user_config, path, hooks_only)
    return FINISH_OP
