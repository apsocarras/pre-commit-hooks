from __future__ import annotations

from typing import NamedTuple


class NodeLoc(NamedTuple):
    """Location of a node within a module"""

    idx: int
    lineno: int
