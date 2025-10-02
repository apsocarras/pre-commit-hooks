from __future__ import annotations

import textwrap

import pytest
from useful_types import (
    SequenceNotStr as Sequence,  # pyright: ignore[reportUnusedImport]
)


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
