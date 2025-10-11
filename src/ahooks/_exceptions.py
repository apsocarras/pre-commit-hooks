from __future__ import annotations

from useful_types import SequenceNotStr as Sequence


class PreCommitYamlValidationError(BaseException):
    """Raise when parsing a YAML goes wrong"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
