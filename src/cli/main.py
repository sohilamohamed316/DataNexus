"""
src/cli/main.py
================
Root Click group for the DataNexus CLI.

All sub-commands and sub-groups are registered here.
The entry point is the `cli` object at the bottom of this file.

Invocation methods
------------------
  # After `pip install -e .`  (entry_points in setup.py/pyproject.toml):
  datanexus <command>

  # Without installation, from the project root:
  python -m src.cli <command>
"""

import sys
from pathlib import Path

import click

# Ensure the project root is importable however this module is loaded
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.cli.commands import (
    seed_cmd,
    run_cmd,
    profile_cmd,
    runs_group,
    config_group,
    sources_group,
    datasets_group,
)


# ─────────────────────────────────────────────────────────────────────────────
# Root group
# ─────────────────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(version="1.0.0", prog_name="datanexus")
def cli() -> None:
    """
    DataNexus — Automated Data Quality & Observability Framework

    \b
    Quick start:
      datanexus seed               # seed demo data (run this first)
      datanexus config list        # see available validation configs
      datanexus run <config-id>    # run a validation and see results
      datanexus runs list          # browse past runs
      datanexus runs show <run-id> # inspect per-check results

    \b
    All commands support --help for full usage details.
    """
    pass


# ── Register every command / group ────────────────────────────────────────────
cli.add_command(seed_cmd)        # datanexus seed
cli.add_command(run_cmd)         # datanexus run <config-id>
cli.add_command(profile_cmd)     # datanexus profile <dataset-id>
cli.add_command(runs_group)      # datanexus runs list | show <id>
cli.add_command(config_group)    # datanexus config list | show <id> | generate
cli.add_command(sources_group)   # datanexus sources list
cli.add_command(datasets_group)  # datanexus datasets list
