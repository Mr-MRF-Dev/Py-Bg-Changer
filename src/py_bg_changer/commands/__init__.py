"""All the commands.

Importing a module registers its commands, so the order of these imports is the order
of the commands in `pbc --help`.
"""

# isort: skip_file
from . import manage, apply, show
from .registry import COMMANDS, all_names

__all__ = ["COMMANDS", "all_names", "apply", "manage", "show"]
