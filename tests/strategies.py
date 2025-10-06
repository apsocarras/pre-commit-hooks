from __future__ import annotations

import typing as t

from hypothesis import strategies as st
from hypothesis.strategies._internal.strategies import SearchStrategy
from useful_types import SequenceNotStr as Sequence

from ahooks._types import HookChoice


def hook_choice_strat() -> SearchStrategy[list[HookChoice]]:
    choices = tuple(t.get_args(h)[0] for h in t.get_args(HookChoice))
    return st.lists(st.sampled_from(choices), min_size=1, max_size=3)
