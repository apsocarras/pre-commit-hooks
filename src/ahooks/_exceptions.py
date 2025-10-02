from __future__ import annotations


class PreCommitYamlValidationError(BaseException):
    """Raise when parsing a YAML goes wrong"""

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
