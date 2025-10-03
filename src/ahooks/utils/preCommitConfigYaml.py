"""Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks"""

from __future__ import annotations

import io
import logging
import warnings
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import Any

import attr
import attrs
import cattrs
from cattrs.converters import Converter
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn
from ruamel.yaml import YAML
from useful_types import SequenceNotStr as Sequence

from ahooks._exceptions import PreCommitYamlValidationError
from ahooks.utils._file_utils import write_atomic

from .._types import (
    FAILED_OP,
    FINISH_OP,
    GitStage,
    HookChoice,
    OpSentinel,
    P,
    R,
)

logger = logging.getLogger(__name__)


def _get_yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True  # added in ruamel.yaml
    yaml.explicit_start = True  # control also available in PyYAML
    yaml.explicit_end = True  #
    yaml.width = 4096  # don't fold long lines
    yaml.preserve_quotes = True
    yaml.default_flow_style = None

    return yaml


yaml = _get_yaml()


def _matches_name(repo_name: str, r: RepoConfigBlock) -> bool:
    return r.repo.strip().lower() == repo_name


@attr.define
class PreCommitConfigYaml:
    """Schema for `.pre-commit-config.yaml` file"""

    repos: list[RepoConfigBlock]
    minimum_pre_commit_version: str | None = attr.field(default=None)

    def extend(self, repo_block: RepoConfigBlock) -> OpSentinel:
        """Search for repo name in the config yaml and append the given hooks

        - If the same name exists, adds to it
        - Else, adds as a new repo block at the end of the yaml
        """
        repo_name = repo_block.repo
        hooks = repo_block.hooks

        def _find_repo_and_append() -> OpSentinel:
            try:
                idx = next(
                    n for n, r in enumerate(self.repos) if _matches_name(repo_name, r)
                )
                exist_hooks: list[HookConfigBlock] = self.repos[idx].hooks
                exist_hook_ids = {h.id for h in exist_hooks}
                for h in hooks:
                    if h.id in exist_hook_ids:
                        warnings.warn(
                            f"Provided yaml already has a hook named {h.id}. Skipping.",
                            stacklevel=2,
                        )
                        continue
                    exist_hooks.append(h)
                if len(exist_hook_ids) == len(exist_hooks):
                    return FAILED_OP
                else:
                    return FINISH_OP
            except StopIteration:
                return FAILED_OP

        if _find_repo_and_append():
            return FINISH_OP

        self.repos.append(repo_block)
        return FINISH_OP

    def append_hooks(self, repo_name: str, *hooks: HookConfigBlock) -> OpSentinel:
        """Search for repo name in the config yaml and append the given hooks

        - If the same name exists, adds to it
        - Else, adds another block at the end of the yaml
        """
        return self.extend(RepoConfigBlock(repo_name, list(hooks)))


@attr.define
class RepoConfigBlock:
    """Repo entry in .pre-commit-config.yaml."""

    repo: str = attr.field(default="local")
    hooks: list[HookConfigBlock] = attr.field(factory=list)

    def add_hook(self, hook: HookConfigBlock) -> None:
        """Append a hook to the end of the hook list"""
        self.hooks.append(hook)


_module_precommit_repo = RepoConfigBlock()


@attr.define
class HookConfigBlock:
    """Decorator for attaching default `.pre-commit-config.yaml` configurations to hooks.

    Corresponds to the `hook` level entries (under `hooks` in the yaml)
    """

    id: str = attr.field()
    name: str | None = attr.field(default=None)
    language: str | None = attr.field(default=None)
    entry: str | None = attr.field(default=None)
    args: tuple[str, ...] | None = attr.field(default=None)
    pass_filenames: bool | None = attr.field(default=None)
    files: str | None = attr.field(default=None)
    stages: tuple[GitStage, ...] | None = attr.field(default=None)

    _repo: RepoConfigBlock = attr.field(
        factory=lambda: _module_precommit_repo, metadata={"omit": True}, alias="_repo"
    )
    _funcs: set[Callable[..., Any]] = attr.field(
        factory=set, init=False, repr=False, metadata={"omit": True}
    )

    def __attrs_post_init__(self) -> None:
        """Registers self with the passed repo config block"""
        self._repo.add_hook(self)

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        """Registers the function with itself (and by extension its repo member)"""
        self._funcs.add(func)
        return func


def _omit_unstructurer(
    cls: type, conv: cattrs.Converter
) -> Callable[..., dict[str, Any]]:
    """Omit if field metadata says to"""
    fn: Callable[[Any], dict[str, Any]] = make_dict_unstructure_fn(
        cls, conv, _cattrs_omit_if_default=True
    )

    def wrapped(inst: attrs.AttrsInstance) -> dict[str, Any]:
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


def dump_config(config: PreCommitConfigYaml, path: Path) -> None:
    """Dump to yaml"""
    des = conv.unstructure(config)
    buf: StringIO = io.StringIO()
    yaml.dump(
        {
            "minimum_pre_commit_version": des["minimum_pre_commit_version"],
            "repos": des["repos"],
        },
        buf,
    )
    write_atomic(path, buf.getvalue())


def load_config(path: Path) -> PreCommitConfigYaml:
    """Load a .pre-commit-config.yaml into a structured object"""
    try:
        with path.open("r") as file:
            config = yaml.load(file)
        return conv.structure(config, PreCommitConfigYaml)
    except cattrs.BaseValidationError as e:
        raise PreCommitYamlValidationError() from e


def get_ahook_config(*hook_choices: HookChoice) -> PreCommitConfigYaml:
    """Create a config yaml from this package's hooks"""
    if hook_choices:
        choice_set = set(hook_choices)
        filtered_hooks = [h for h in _module_precommit_repo.hooks if h.id in choice_set]
        filtered_repo = RepoConfigBlock(hooks=filtered_hooks)
        return PreCommitConfigYaml(repos=[filtered_repo])
    else:
        return PreCommitConfigYaml(repos=[_module_precommit_repo])


def dump_ahook_config(path: Path, *hooks: HookChoice) -> OpSentinel:
    """Open the config yaml and append the packages's hooks (if the file exists) or create a new config.yaml"""
    module_config: PreCommitConfigYaml = get_ahook_config(*hooks)

    if not path.exists():
        dump_config(module_config, path)
        return FINISH_OP

    user_config: PreCommitConfigYaml = load_config(path)
    append_result: OpSentinel = user_config.extend(repo_block=module_config.repos[0])

    if not append_result:
        return FAILED_OP
    else:
        dump_config(user_config, path)
    return FINISH_OP
