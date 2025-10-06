from __future__ import annotations

from pathlib import Path

from useful_types import SequenceNotStr as Sequence

from ahooks.utils.preCommitConfigYaml import (
    PreCommitConfigYaml,
    dump_config,
    load_config,
)
from tests.conftest import YamlFile


def test_roundtrip_yaml(expected_ahook_yaml: YamlFile, tmpdir):
    """Test that reading yaml and dumping yaml matches given file format"""
    res: PreCommitConfigYaml = load_config(expected_ahook_yaml.path)
    assert isinstance(res, PreCommitConfigYaml)
    dump_config(res, (new := (Path(__file__).parent / "temp.yaml")), False)
    assert expected_ahook_yaml.path.read_text() == new.read_text()
