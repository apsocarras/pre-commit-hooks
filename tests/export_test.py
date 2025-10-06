from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from ruamel.yaml import YAML
from useful_types import SequenceNotStr as Sequence

from ahooks._types import HookChoice
from ahooks.export import export
from ahooks.utils.preCommitConfigYaml import (
    HookConfigBlock,
    PreCommitConfigYaml,
    load_config,
    load_hooks,
)
from tests.strategies import hook_choice_strat

yaml = YAML()


_base_pre_commit_config_yaml_path = path = (
    Path(__file__).parent / ".test.pre-commit-hooks.yaml"
)
_base_pre_commit_config_yaml = load_config(_base_pre_commit_config_yaml_path)


def get_expected_yaml(*include: HookChoice) -> PreCommitConfigYaml:
    """Form the expected yaml structure from the hooks included (if provided - defaults to all hooks)"""
    repo = _base_pre_commit_config_yaml.repos[0]
    if include:
        repo.hooks = list[HookConfigBlock](h for h in repo.hooks if h.id in include)
    return PreCommitConfigYaml(
        repos=[repo],
        minimum_pre_commit_version=_base_pre_commit_config_yaml.minimum_pre_commit_version,
    )


def check_yaml_vs_expected(
    given: PreCommitConfigYaml, expected: PreCommitConfigYaml
) -> None:
    assert given == expected


def check_hooks_vs_expected(
    given: Sequence[HookConfigBlock], expected: Sequence[HookConfigBlock]
) -> None:
    assert given == expected


def check(output: Path, expected_pc_yaml: PreCommitConfigYaml, hooks_only: bool):
    if not hooks_only:
        loaded_output_config = load_config(output)
        check_yaml_vs_expected(loaded_output_config, expected_pc_yaml)
    else:
        loaded_output_hooks = load_hooks(output)
        check_hooks_vs_expected(loaded_output_hooks, expected_pc_yaml.repos[0].hooks)


@pytest.mark.parametrize("hooks_only", (True, False))
@given(hook_choice_strat())
def test_export_given_hooks(hooks: list[HookChoice], hooks_only: bool, tmpdir):
    expected_pc_yaml = get_expected_yaml(*hooks)
    output = Path(tmpdir) / f".given_hooks-{'hooks' if hooks_only else 'config'}.yaml"
    export(hooks, config_path=output, hooks_only=hooks_only)

    check(output, expected_pc_yaml, hooks_only)


@pytest.mark.parametrize("hooks_only", (True, False))
def test_export_no_hooks(hooks_only: bool, tmpdir):
    expected_pc_yaml = get_expected_yaml()
    output = Path(tmpdir) / f".no_hooks-{'hooks' if hooks_only else 'config'}.yaml"
    export(config_path=output, hooks_only=False)

    check(output, expected_pc_yaml, hooks_only)
