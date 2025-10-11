from __future__ import annotations

import ast
from typing import Any

from useful_types import SequenceNotStr as Sequence


def get_target_id(node: ast.AnnAssign) -> str | Any | None:
    if isinstance(node.target, ast.Name):
        return node.target.id
    elif isinstance(node.target, ast.Attribute):
        next_node = getattr(node.value, "value", None)
        while next_node:
            if isinstance(next_node, ast.Name):
                return next_node.id
            next_node = getattr(next_node.value, "value", None)

        return getattr(node.target.value, "id", None)
    else:  # ast.Subscript
        return getattr(node.target.value, "id", None)


def is_sequence_str_annotation(o: object) -> bool:
    """Call on a node's `annotation` member

    Example:
    -------
    AnnAssign(
    target=Name(id='b', ctx=Store()),
    annotation=Subscript(
        value=Name(id='Annotated', ctx=Load()),
        slice=Tuple(
            elts=[
                Subscript(
                    value=Name(id='Sequence', ctx=Load()),
                    slice=Name(id='str', ctx=Load()),
                    ctx=Load()),
                Constant(value='metadata')],
            ctx=Load()),
        ctx=Load()),
    simple=1)

    """
    # if it's a type alias
    return (
        isinstance(o, ast.Subscript)
        and getattr(o.value, "id", None) == "Sequence"
        and getattr(o.slice, "id", None) == "str"
    )


def has_str_in_union_annotation(o: object) -> bool:
    return isinstance(o, ast.BinOp)
