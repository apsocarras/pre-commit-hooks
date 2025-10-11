from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from useful_types import SequenceNotStr as Sequence


@runtime_checkable
class HasWrite(Protocol):
    """Proto for files or buffer"""

    def write(self, s: str, /) -> int: ...


def write_(f: HasWrite, s: str) -> None:
    """Write wrapper to placate pyright"""
    f.write(s)  # pyright: ignore[reportUnusedCallResult]


def write_atomic(path: Path, new_content: str) -> None:
    """Write to tmp first, then replace."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        write_(f, new_content)
    _ = tmp.replace(path)


def write_if_changed(path: Path, content: str) -> bool:
    """Write a file only if it's changed. Use this for files not tracked in `.git`"""
    old = path.read_text() if path.exists() else None
    if old == content:
        return False
    write_atomic(path, content)
    return True
