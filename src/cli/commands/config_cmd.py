"""
src/cli/commands/config_cmd.py
================================
`config` command group:

  datanexus config list
      Shows a table of all ValidationConfigs in the database.

  datanexus config show <config-id>
      Shows config metadata + the raw YAML stored in the database.

  datanexus config generate [--output FILE]
      Prints a ready-to-use YAML config template to stdout or a file.
      Useful as a starting point for writing your own validation config.
"""

import sys
from pathlib import Path

import click

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.database import get_db_session
from src.database.models import ValidationConfig, Dataset, DataSource
from src.cli.formatting import print_table, print_section


# ─────────────────────────────────────────────────────────────────────────────
# Template YAML — used by `config generate`
# ─────────────────────────────────────────────────────────────────────────────

_TEMPLATE_YAML = """\
# DataNexus Validation Config — Template
# ---------------------------------------
# Replace placeholders below and load this config into the database
# (direct DB insert or via the future REST API endpoint).

dataset: your_table_name           # must match datasets.table_name
name: My Validation Config
description: Describe what this config validates.
quality_threshold: 80.0            # run FAILS if score drops below this (0–100)
alert_channels: []                 # options: [slack, email] — Step 7

checks:
  # ── Completeness: column must not be empty ─────────────────────────────────
  - name: email_not_empty
    column: email
    check_type: not_empty
    threshold: 0.95     # 95% of rows must pass this check
    severity: high      # options: low | medium | high | critical

  # ── Range: numeric values must fall inside [min, max] ─────────────────────
  - name: age_in_range
    column: age
    check_type: range
    min_value: 18
    max_value: 120
    threshold: 1.0
    severity: medium

  # ── Uniqueness: no duplicate values allowed ────────────────────────────────
  - name: id_unique
    column: customer_id
    check_type: unique
    threshold: 1.0
    severity: critical

  # ── Value set: column must contain only accepted values ────────────────────
  - name: status_valid
    column: status
    check_type: in_set
    accepted_values: [active, inactive, pending]
    threshold: 1.0
    severity: high

  # ── Regex: column values must match a pattern ──────────────────────────────
  # - name: phone_format
  #   column: phone
  #   check_type: regex
  #   pattern: '^\\+?[0-9]{7,15}$'
  #   threshold: 0.90
  #   severity: low

# Supported check_type values:
#   not_null | completeness | not_empty | unique | range
#   regex | in_set | foreign_key | referential_integrity | freshness
#
# Severity weight in quality score:
#   critical=1.0  high=0.75  medium=0.5  low=0.25
"""


# ─────────────────────────────────────────────────────────────────────────────
# Group
# ─────────────────────────────────────────────────────────────────────────────

@click.group("config")
def config_group() -> None:
    """Manage and inspect validation configs."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# datanexus config list
# ─────────────────────────────────────────────────────────────────────────────

@config_group.command("list")
@click.option("--all", "show_all", is_flag=True, default=False,
              help="Include inactive (is_active=False) configs.")
def config_list(show_all: bool) -> None:
    """
    List all validation configs in the database.

    \b
    Examples:
      datanexus config list
      datanexus config list --all
    """
    try:
        with get_db_session() as session:
            query = session.query(ValidationConfig)
            if not show_all:
                query = query.filter_by(is_active=True)
            configs = query.order_by(ValidationConfig.id).all()

            if not configs:
                click.echo("\n  No validation configs found.")
                click.echo("  Run `datanexus seed` to create demo configs.\n")
                return

            rows = []
            for c in configs:
                dataset = session.query(Dataset).filter_by(id=c.dataset_id).first()
                table   = dataset.table_name if dataset else "?"
                threshold_pct = f"{c.quality_threshold * 100:.0f}%"
                check_count   = _count_checks(c.config_yaml)
                rows.append([
                    c.id,
                    c.name[:40],
                    table,
                    threshold_pct,
                    check_count,
                    c.schedule_cron or "—",
                    "yes" if c.is_active else "no",
                ])

        print_table(
            headers=["ID", "Name", "Dataset", "Threshold", "Checks", "Schedule", "Active"],
            rows=rows,
            title=f"Validation Configs  ({len(rows)} found)",
        )
        click.echo()

    except Exception as exc:
        click.echo(f"\n  Error: {exc}\n")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# datanexus config show <config-id>
# ─────────────────────────────────────────────────────────────────────────────

@config_group.command("show")
@click.argument("config_id", type=int)
def config_show(config_id: int) -> None:
    """
    Show the metadata and YAML for one validation config.

    CONFIG_ID is the integer id from the validation_configs table.

    \b
    Examples:
      datanexus config show 1
    """
    try:
        with get_db_session() as session:
            cfg = session.query(ValidationConfig).filter_by(id=config_id).first()
            if cfg is None:
                click.echo(f"\n  Error: No ValidationConfig with id={config_id} found.")
                click.echo("  Run `datanexus config list` to see available configs.\n")
                sys.exit(1)

            dataset = session.query(Dataset).filter_by(id=cfg.dataset_id).first()
            source  = session.query(DataSource).filter_by(id=dataset.source_id).first() if dataset else None

            print_section(f"Config  #{config_id}  —  {cfg.name}")
            click.echo(f"  ID          : {cfg.id}")
            click.echo(f"  Name        : {cfg.name}")
            click.echo(f"  Description : {getattr(cfg, 'description', None) or '—'}")
            click.echo(f"  Dataset     : [{cfg.dataset_id}] {dataset.table_name if dataset else '?'}")
            click.echo(f"  Source      : {source.name if source else '?'}")
            click.echo(f"  Threshold   : {cfg.quality_threshold * 100:.0f}%")
            click.echo(f"  Schedule    : {cfg.schedule_cron or '—'}")
            click.echo(f"  Alerts      : {'yes' if cfg.alert_on_failure else 'no'}  "
                       f"({cfg.alert_channels or 'none'})")
            click.echo(f"  Active      : {'yes' if cfg.is_active else 'no'}")
            click.echo(f"  Created     : {cfg.created_at}")
            click.echo(f"  Checks      : {_count_checks(cfg.config_yaml)}")

            print_section("YAML Content")
            click.echo()
            for line in cfg.config_yaml.splitlines():
                click.echo(f"    {line}")
            click.echo()

    except SystemExit:
        raise
    except Exception as exc:
        click.echo(f"\n  Error: {exc}\n")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# datanexus config generate [--output FILE]
# ─────────────────────────────────────────────────────────────────────────────

@config_group.command("generate")
@click.option("--output", "-o", default=None, type=click.Path(),
              help="Write template to a file instead of printing to stdout.")
def config_generate(output: str) -> None:
    """
    Print a validation config YAML template.

    Prints an annotated template showing all supported check types.
    Redirect stdout or use --output to save it to a file.

    \b
    Examples:
      datanexus config generate
      datanexus config generate --output config/examples/my_config.yaml
    """
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_TEMPLATE_YAML, encoding="utf-8")
        click.echo(f"\n  Template written to: {path}\n")
    else:
        click.echo()
        click.echo(_TEMPLATE_YAML)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _count_checks(config_yaml: str) -> int:
    """Quick count of checks without fully parsing YAML."""
    try:
        import yaml
        parsed = yaml.safe_load(config_yaml)
        return len(parsed.get("checks", []))
    except Exception:
        return "?"
