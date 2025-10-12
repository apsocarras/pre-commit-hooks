from __future__ import annotations

from pathlib import Path

import pytest
from useful_types import SequenceNotStr as Sequence

from ahooks.models import (
    HookConfigBlock,
    PreCommitConfigYaml,
    RepoConfigBlock,
    conv,
    dump_config,
    load_config,
    load_hooks,
)
from tests.conftest import YamlFile


@pytest.mark.parametrize("hooks_only", (True, False))
def test_roundtrip_yaml(
    expected_ahook_yaml: YamlFile,
    expected_ahook_just_hooks_yaml: YamlFile,
    hooks_only: bool,
    tmpdir,
):
    """Test that reading yaml and dumping yaml matches given file format"""
    if not hooks_only:
        expected = expected_ahook_yaml
        res = load_config(expected.path)
        assert isinstance(res, PreCommitConfigYaml)
        dump_config(
            res, (new := (Path(__file__).parent / "temp-config.yaml")), hooks_only
        )
    else:
        expected = expected_ahook_just_hooks_yaml
        hooks = load_hooks(expected.path)
        res = PreCommitConfigYaml(repos=[RepoConfigBlock("local", hooks)])
        dump_config(
            res, (new := (Path(__file__).parent / "temp-hooks.yaml")), hooks_only
        )

    assert expected.path.read_text() == new.read_text()


def test_res_hooks_only():
    data = [
        {
            "id": "add-from-future",
            "name": "Add `from __future__ import annotations` to `.py` files.",
            "language": "python",
            "entry": "python -m ahooks.add_from_future",
            "args": ["-ds"],
            "pass_filenames": False,
            "files": "^.*\\.py$",
            "stages": ["pre-commit"],
        },
        {
            "id": "block-manual-req-edits",
            "name": "Block manual edits to requirements.txt",
            "language": "system",
            "entry": '\n     bash -c\n            if git diff --cached --name-only | grep -q "^requirements\\.txt$" &&\n                ! git diff --cached --name-only | grep -q "^pyproject\\.toml$"; then\n                echo "Edit pyproject.toml and run the emitter; don\'t hand-edit requirements.txt."\n                exit 1\n            fi\n    ',
            "pass_filenames": False,
            "files": "^requirements\\.txt$",
            "stages": ["pre-commit", "pre-push"],
        },
        {
            "id": "emit-requirements",
            "name": "Emit requirements.txt from pyproject.toml using `uv`",
            "language": "system",
            "entry": "python -m ahooks.emit_requirements",
            "pass_filenames": False,
            "files": "^(pyproject\\.toml|requirements\\.txt)$",
            "stages": ["pre-commit", "pre-push"],
        },
        {
            "id": "env-skeleton",
            "name": "Create an example `.env` file with only the names of variables",
            "language": "system",
            "entry": "python -m ahooks.env_skeleton",
            "args": [".", ".env", "."],
            "pass_filenames": False,
            "stages": ["pre-commit", "pre-push"],
        },
    ]

    _ = conv.structure(data, list[HookConfigBlock])
