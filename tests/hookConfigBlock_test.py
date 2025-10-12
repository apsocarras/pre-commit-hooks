from __future__ import annotations

import pytest
from useful_types import SequenceNotStr as Sequence

from ahooks._types import HookChoice, iter_hook_choices
from ahooks.models import HookConfigBlock as hb
from ahooks.models import RepoConfigBlock as r


def test_hook_decorator_registry():
    repo = r("my-repo")

    @hb(
        id="add-from-future",
        name="Add `from __future__ import annotations` to `.py` files.",
        language="python",
        entry="python -m ahooks.add_from_future",
        args=("-ds",),
        pass_filenames=False,
        files=r"^.*\.py$",
        stages=("commit",),
        _repo=repo,
    )
    def some_func():
        return

    assert len(repo.hooks) == 1
    assert some_func in repo.hooks[0]._funcs


@pytest.mark.parametrize(
    ("hooks"),
    (
        None,
        "add-from-future",
        "env-skeleton",
        "emit-requirements",
        ("add-from-future", "env-skeleton", "emit-requirements"),
    ),
)
def test_module_repo_has_hook_decorators(
    hooks: HookChoice | tuple[HookChoice, ...] | None,
):
    from ahooks.models import get_ahook_config

    match hooks:
        case str():
            module_config = get_ahook_config(hooks)
            expected_len = 1
        case None:
            module_config = get_ahook_config()
            expected_len = len(tuple(iter_hook_choices()))
        case _:
            module_config = get_ahook_config(*hooks)
            expected_len = len(hooks)

    if len(module_config.repos[0].hooks) != expected_len:
        raise RuntimeError(tuple(h.id for h in module_config.repos[0].hooks))
