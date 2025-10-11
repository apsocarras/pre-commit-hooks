# from __future__ import annotations


from __future__ import annotations

import os
import shutil
import typing
import uuid
from collections.abc import Collection, Iterable
from itertools import chain
from pathlib import Path
from typing import TypedDict

import pytest
from click.testing import CliRunner, Result
from hypothesis import HealthCheck, given, settings
from ruamel.yaml import YAML
from typing_extensions import NotRequired, Unpack
from useful_types import SequenceNotStr as Sequence

from ahooks._types import HookChoice
from ahooks.export import export
from ahooks.utils.preCommitConfigYaml import (
    HookConfigBlock,
    PreCommitConfigYaml,
    get_ahook_config,
    load_config,
    load_hooks,
)
from tests.strategies import hook_choice_strat

yaml = YAML()


def _check_yaml_vs_expected(
    given: PreCommitConfigYaml, expected: PreCommitConfigYaml
) -> None:
    assert given.repos[0].repo == expected.repos[0].repo
    gh = {h.id for h in given.repos[0].hooks}
    eh = {h.id for h in expected.repos[0].hooks}
    assert gh == eh


def _check_hooks_vs_expected(
    given: Sequence[HookConfigBlock], expected: Sequence[HookConfigBlock]
) -> None:
    assert given == expected


def _check(output: Path, expected: PreCommitConfigYaml, hooks_only: bool) -> None:
    if not hooks_only:
        loaded_output_config = load_config(output)
        _check_yaml_vs_expected(loaded_output_config, expected)
    else:
        ## Before writing output, the `export` CLI automatically renames a `pre-commit-config.yaml` path
        # to `pre-commit-hooks.yaml`.
        # In this validation function, need to modify the passed parameter to match
        assert output.name == ".pre-commit-config.yaml"  # ensure expected test behavior
        hooks_path = output.parent / ".pre-commit-hooks.yaml"
        loaded_output_hooks = load_hooks(hooks_path)
        _check_hooks_vs_expected(loaded_output_hooks, expected.repos[0].hooks)


class _CallExportKwargs(TypedDict, total=False):
    hooks: NotRequired[Collection[HookChoice]]
    config_path: NotRequired[Path]
    hooks_only: NotRequired[bool]


def _call_export(**kwargs: Unpack[_CallExportKwargs]) -> Result:
    hooks = kwargs.get("hooks")
    config_path = kwargs.get("config_path")
    hooks_only = kwargs.get("hooks_only")

    args: list[str] = []
    if hooks:
        args += list(chain.from_iterable(("-k", h) for h in hooks))
    if config_path:
        args += ["-o", str(config_path)]
    if hooks_only:
        args += ["-h"]

    runner = CliRunner()
    result = runner.invoke(export, args, standalone_mode=False)
    assert result.exit_code == 0, result.output
    return result


def _iter_hook_choices() -> Iterable[HookChoice]:
    for lit in typing.get_args(HookChoice):
        yield typing.get_args(lit)[0]


def _ahook_runner(config: PreCommitConfigYaml, *obj: HookChoice) -> None:
    if not obj:
        obj = tuple(_iter_hook_choices())

    ## The hypothesis strategy can generate duplicate hook choices
    # Ensure that the generating function handles this
    de_duped = list(set(obj))

    given, exp = sorted(config.repos[0].hooks, key=lambda h: h.id), sorted(de_duped)
    assert len(given) == len(exp)
    # assert config.repos[0].hooks == obj # wrong -- obj is just the list of ids/names
    for n, _ in enumerate(given):
        assert given[n].id == exp[n]


@given(obj=hook_choice_strat())
def test_get_ahook_config_given_hooks(obj: list[HookChoice]) -> None:
    """Test function for generating new yaml configs from lists of hooks"""
    config = get_ahook_config(*obj)
    _ahook_runner(config, *obj)


def test_get_ahook_config_no_hooks_given():
    """Test function for generating new yaml configs from lists of hooks"""
    config = get_ahook_config()
    _ahook_runner(config)


def _export_runner(hooks_only: bool, given_hooks: list[HookChoice] | None) -> None:
    output = (
        Path(__file__).parent
        / "example_exports"
        / f"{uuid.uuid4()}"
        / ".pre-commit-config.yaml"
    )
    os.mkdir(output.parent)
    try:
        expected = get_ahook_config(*given_hooks) if given_hooks else get_ahook_config()
        kwargs: _CallExportKwargs = {
            "config_path": output,
            "hooks_only": hooks_only,
        }
        if given_hooks:
            kwargs["hooks"] = given_hooks
        _res = _call_export(**kwargs)
        _check(output, expected, hooks_only)
    finally:
        shutil.rmtree(output.parent)


@given(obj=hook_choice_strat().filter(lambda x: "block-manual-req-edits" not in x))
@pytest.mark.parametrize("hooks_only", (True, False))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
def test_export_given_hooks(hooks_only: bool, obj: list[HookChoice]) -> None:
    _export_runner(hooks_only, obj)


@pytest.mark.parametrize("hooks_only", (True, False))
def test_export_no_hooks_given(hooks_only: bool) -> None:
    _export_runner(hooks_only, given_hooks=None)
