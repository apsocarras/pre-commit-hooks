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
from typing_extensions import override
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

        try:
            idx = next(
                n for n, r in enumerate(self.repos) if _matches_name(repo_name, r)
            )
        except StopIteration:
            idx = max(len(self.repos) - 1, 0)

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

    def append_hooks(self, repo_name: str, *hooks: HookConfigBlock) -> OpSentinel:
        """Search for repo name in the config yaml and append the given hooks

        - If the same name exists, adds to it
        - Else, adds another block at the end of the yaml
        """
        return self.extend(RepoConfigBlock(repo_name, list(hooks)))

    @override
    def __eq__(self, o: object) -> bool:
        """Compares only repo blocks in each yaml file, ignoring sort order"""
        if not isinstance(o, PreCommitConfigYaml) or not len(o.repos) == len(
            self.repos
        ):
            return False
        _s = sorted(self.repos, key=lambda r: r.repo)
        _o = sorted(o.repos, key=lambda r: r.repo)
        return all(s == o for s, o in zip(_s, _o, strict=False))


@attr.define
class RepoConfigBlock:
    """Repo entry in .pre-commit-config.yaml."""

    repo: str
    hooks: list[HookConfigBlock] = attr.field(factory=list)

    def add_hook(self, hook: HookConfigBlock, guard: bool = False) -> None:
        """Append a hook to the end of the hook list"""
        if guard and self.has_hook(hook):
            return
        self.hooks.append(hook)

    def has_hook(self, hook: HookConfigBlock) -> bool:
        """Checks if a hook of the same id is already in the hook list"""
        has_ = any(h.id == hook.id for h in self.hooks)
        logger.debug(msg=tuple(h.id for h in self.hooks))
        return has_

    @override
    def __eq__(self, o: object, /) -> bool:
        if not isinstance(o, RepoConfigBlock) or not len(o.hooks) == len(self.hooks):
            return False
        _s = sorted(self.hooks, key=lambda h: h.id)
        _o = sorted(o.hooks, key=lambda h: h.id)
        return all(s == o for s, o in zip(_s, _o, strict=False))


_module_precommit_repo = RepoConfigBlock(repo="local")


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
        self._repo.add_hook(self, guard=True)

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        """Registers the function with itself (and by extension its repo member)"""
        self._funcs.add(func)
        return func

    @override
    def __eq__(self, o: object, /) -> bool:
        """Only compares id parameter (for my purposes this is sufficient)"""
        return isinstance(o, HookConfigBlock) and o.id == self.id


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
    if hook_choices:
        choice_set = set(hook_choices)
        filtered_hooks = [h for h in _module_precommit_repo.hooks if h.id in choice_set]
        filtered_repo = RepoConfigBlock(repo="local", hooks=filtered_hooks)
        return PreCommitConfigYaml(repos=[filtered_repo])
    else:
        return PreCommitConfigYaml(repos=[_module_precommit_repo])


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
