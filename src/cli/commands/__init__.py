# src/cli/commands/__init__.py
# Exports all Click commands/groups for registration in main.py
from .seed_cmd    import seed_cmd
from .run_cmd     import run_cmd, profile_cmd
from .results_cmd import runs_group
from .config_cmd  import config_group
from .sources_cmd import sources_group, datasets_group

__all__ = [
    "seed_cmd",
    "run_cmd",
    "profile_cmd",
    "runs_group",
    "config_group",
    "sources_group",
    "datasets_group",
]
