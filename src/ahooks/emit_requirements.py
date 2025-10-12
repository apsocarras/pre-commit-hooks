from __future__ import annotations

from useful_types import SequenceNotStr as Sequence

from .hooks.emit_requirements import emit_requirements

if __name__ == "__main__":
    emit_requirements()
