from __future__ import annotations

import logging

from ruamel.yaml import YAML
from useful_types import SequenceNotStr as Sequence

logger = logging.getLogger(__name__)


def _get_yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True
    yaml.explicit_start = True
    yaml.explicit_end = True
    yaml.width = 4096  # don't fold long lines
    yaml.preserve_quotes = True
    yaml.default_flow_style = None

    return yaml


yaml = _get_yaml()
