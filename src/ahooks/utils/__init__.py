"""
Yes, the dreaded "`utils`" folder.

I trust that the files themselves are named well enough.
"""

from __future__ import annotations

from useful_types import SequenceNotStr as Sequence

from .preCommitConfigYaml import HookConfigBlock, PreCommitConfigYaml, RepoConfigBlock

__all__ = [
    "HookConfigBlock",
    "PreCommitConfigYaml",
    "RepoConfigBlock",
]
