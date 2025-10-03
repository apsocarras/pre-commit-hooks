from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from ruamel.yaml import YAML
from useful_types import (
    SequenceNotStr as Sequence,  # pyright: ignore[reportUnusedImport]
)

yaml = YAML()


@pytest.fixture(scope="session")
def sample_toml_file() -> str:
    s = textwrap.dedent("""
            [project]
        name = "test"
        version = "0.1.0"
        description = "Testing toml for emit-requirements hook"
        readme = "README.md"
        authors = [
            { name = "Alexander Socarras", email = "apsocarras@gmail.com" }
        ]
        requires-python = ">=3.11"
        dependencies = []

        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"
    """)
    return s


class YamlFile(NamedTuple):
    path: Path
    data: Any


@pytest.fixture(scope="session")
def expected_ahook_yaml() -> YamlFile:
    """Expected format of the `.pre-commit-config.yaml` output by `ahook.export.py`"""
    path = Path(__file__).parent / ".test.pre-commit-config.yaml"
    with path.open("r") as file:
        data = yaml.load(file)
    return YamlFile(path, data)
