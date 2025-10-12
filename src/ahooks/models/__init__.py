"""Models representing the `.pre-commit-config.yaml` file and the blocks contained in it."""

from __future__ import annotations

from useful_types import SequenceNotStr as Sequence

from .converters import (
    conv,
    dump_ahook_config,
    dump_config,
    get_ahook_config,
    load_config,
    load_hooks,
)
from .hookConfigBlock import HookConfigBlock
from .preCommitConfigYaml import PreCommitConfigYaml
from .repoConfigBlock import RepoConfigBlock

__all__ = [
    "HookConfigBlock",
    "PreCommitConfigYaml",
    "RepoConfigBlock",
    "conv",
    "dump_ahook_config",
    "dump_config",
    "get_ahook_config",
    "load_config",
    "load_hooks",
]
