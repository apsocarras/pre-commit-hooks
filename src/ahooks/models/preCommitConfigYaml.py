"""Schema for `.pre-commit-config.yaml` file"""

from __future__ import annotations

import logging
import warnings

import attr
from typing_extensions import override
from useful_types import SequenceNotStr as Sequence

from .._types import (
    FAILED_OP,
    FINISH_OP,
    OpSentinel,
)
from ..models.hookConfigBlock import HookConfigBlock
from .repoConfigBlock import RepoConfigBlock

logger = logging.getLogger(__name__)


@attr.define
class PreCommitConfigYaml:
    """Schema for `.pre-commit-config.yaml` file"""

    repos: list[RepoConfigBlock]
    minimum_pre_commit_version: str | None = attr.field(default=None)

    @staticmethod
    def _matches_name(repo_name: str, r: RepoConfigBlock) -> bool:
        return r.repo.strip().lower() == repo_name

    def extend(self, repo_block: RepoConfigBlock) -> OpSentinel:
        """Search for repo name in the config yaml and append the given hooks

        - If the same name exists, adds to it
        - Else, adds as a new repo block at the end of the yaml
        """
        repo_name = repo_block.repo
        hooks = repo_block.hooks

        try:
            idx = next(
                n for n, r in enumerate(self.repos) if self._matches_name(repo_name, r)
            )
        except StopIteration:
            idx = max(len(self.repos) - 1, 0)

        exist_hooks = self.repos[idx].hooks
        exist_hook_ids = {h.id for h in exist_hooks}
        dups = []
        for h in hooks:
            if h.id in exist_hook_ids:
                dups.append(h.id)
                continue
            exist_hooks.append(h)
        if dups:
            lines = "\n- ".join(dups)
            warnings.warn(
                f"Provided yaml already has hooks:\n- {lines}.",
                stacklevel=2,
            )

        if len(exist_hook_ids) == len(exist_hooks):
            return FAILED_OP
        else:
            return FINISH_OP

    def append_hooks(self, repo_name: str, *hooks: HookConfigBlock) -> OpSentinel:
        """Search for repo name in the config yaml and append the given hooks

        - If the same name exists, adds to it
        - Else, adds another block at the end of the yaml
        """
        return self.extend(RepoConfigBlock(repo_name, list(hooks)))  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]

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
