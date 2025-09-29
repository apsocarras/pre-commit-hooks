from __future__ import annotations

from pathlib import Path

import click

READ_DIR_TYPE = click.Path(
    exists=True, file_okay=False, dir_okay=True, path_type=Path, readable=True
)

READ_FILE_TYPE = click.Path(
    exists=True, file_okay=True, dir_okay=False, path_type=Path, readable=True
)
WRITE_FILE_TYPE = click.Path(
    exists=False, file_okay=True, dir_okay=False, path_type=Path, writable=True
)

WRITE_DIR_TYPE = click.Path(
    exists=True, file_okay=False, dir_okay=True, path_type=Path, writable=True
)
