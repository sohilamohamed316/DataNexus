"""
src/cli/commands/seed_cmd.py
============================
`datanexus seed [--reset]`

Seeds the database with demo data so every other CLI command has
something real to run against without needing a live external database.

What it creates
---------------
  data/sample_customers.csv    — 20 rows with deliberate quality issues
  data_sources       1 row     — CSV source pointing at the file above
  datasets           1 row     — "sample_customers" table entry
  validation_configs 2 rows    — "Basic" (3 checks) and "Strict" (5 checks)

Idempotent by default: safe to run twice; use --reset to wipe and re-seed.
"""

import csv
import sys
from pathlib import Path

import click

# ── Resolve project root so imports work however the CLI is invoked ──────────
_HERE        = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[3]   # src/cli/commands/ → src/cli/ → src/ → project root
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text

from src.database import get_db_session
from src.database.models import DataSource, Dataset, SourceType, ValidationConfig


# ─────────────────────────────────────────────────────────────────────────────
# Sample CSV rows — 20 rows with deliberate quality issues baked in
# ─────────────────────────────────────────────────────────────────────────────
#
# Issues planted for demo visibility:
#   - 3 rows have empty email      → email_not_empty check will FAIL
#   - 3 rows have age outside 18–120 → age_in_range check will FAIL
#   - 1 duplicate customer_id (18) → id_unique check will FAIL
#   - 2 rows have invalid status   → status_valid check (strict) will FAIL

_SAMPLE_CSV_ROWS = [
    ["customer_id", "name",           "email",                   "age", "status"],
    [1,  "Alice Johnson",  "alice@example.com",       25,  "active"],
    [2,  "Bob Smith",      "bob@example.com",         30,  "active"],
    [3,  "Carol White",    "carol@example.com",       22,  "inactive"],
    [4,  "Dave Brown",     "dave@example.com",        45,  "active"],
    [5,  "Eve Davis",      "eve@example.com",         28,  "pending"],
    [6,  "Frank Miller",   "frank@example.com",       35,  "active"],
    [7,  "Grace Wilson",   "grace@example.com",       19,  "inactive"],
    [8,  "Hank Moore",     "hank@example.com",        52,  "active"],
    [9,  "Iris Taylor",    "",                        33,  "active"],    # empty email
    [10, "Jack Anderson",  "",                        200, "active"],    # empty email + age=200
    [11, "Karen Thomas",   "karen@example.com",       41,  "active"],
    [12, "Leo Jackson",    "leo@example.com",         16,  "active"],    # age=16 (underage)
    [13, "Mia Harris",     "mia@example.com",         29,  "active"],
    [14, "Nick Martin",    "nick@example.com",        38,  "unknown"],   # invalid status
    [15, "Olivia Garcia",  "olivia@example.com",      24,  "active"],
    [16, "Paul Martinez",  "",                        31,  "pending"],   # empty email
    [17, "Quinn Robinson", "quinn@example.com",       27,  "inactive"],
    [18, "Rachel Clark",   "rachel@example.com",      44,  "active"],
    [19, "Sam Rodriguez",  "sam@example.com",         36,  "suspended"], # invalid status
    [18, "Tom Lewis",      "tom@example.com",         50,  "active"],    # duplicate id=18
]

_BASIC_CONFIG_YAML = """\
dataset: sample_customers
name: Basic Customer Checks
description: Checks email completeness, age range, and id uniqueness.
quality_threshold: 80.0
alert_channels: []
checks:
  - name: email_not_empty
    column: email
    check_type: not_empty
    threshold: 0.90
    severity: high

  - name: age_in_range
    column: age
    check_type: range
    min_value: 18
    max_value: 120
    threshold: 0.85
    severity: medium

  - name: id_unique
    column: customer_id
    check_type: unique
    threshold: 1.0
    severity: critical
"""

_STRICT_CONFIG_YAML = """\
dataset: sample_customers
name: Strict Customer Checks
description: All basic checks plus status validation and name completeness.
quality_threshold: 90.0
alert_channels: []
checks:
  - name: email_not_empty
    column: email
    check_type: not_empty
    threshold: 0.95
    severity: high

  - name: age_in_range
    column: age
    check_type: range
    min_value: 18
    max_value: 120
    threshold: 0.90
    severity: high

  - name: id_unique
    column: customer_id
    check_type: unique
    threshold: 1.0
    severity: critical

  - name: status_valid
    column: status
    check_type: in_set
    accepted_values: [active, inactive, pending]
    threshold: 1.0
    severity: high

  - name: name_not_empty
    column: name
    check_type: not_empty
    threshold: 1.0
    severity: medium
"""


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(_SAMPLE_CSV_ROWS)
    click.echo(f"  [CSV]    Created {path}  ({len(_SAMPLE_CSV_ROWS) - 1} data rows)")


def _reset(session) -> None:
    """Delete all rows created by a previous seed run and reset all ID sequences to 1."""
    for name in ("Basic Customer Checks", "Strict Customer Checks"):
        for c in session.query(ValidationConfig).filter_by(name=name).all():
            session.delete(c)
    for d in session.query(Dataset).filter_by(table_name="sample_customers").all():
        session.delete(d)
    for s in session.query(DataSource).filter_by(name="DataNexus Demo — CSV").all():
        session.delete(s)
    session.flush()

    sequences = [
        "data_sources_id_seq",
        "datasets_id_seq",
        "validation_configs_id_seq",
        "validation_runs_id_seq",
        "validation_results_id_seq",
        "data_profiles_id_seq",
        "alerts_id_seq",
        "test_definitions_id_seq",
    ]
    for seq in sequences:
        session.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))

    click.echo("  [RESET]  Existing seed data removed and ID sequences restarted.")


def _seed(csv_path: Path) -> dict:
    with get_db_session() as session:
        existing = session.query(DataSource).filter_by(name="DataNexus Demo — CSV").first()
        if existing:
            click.echo("  [SKIP]   DataSource already exists — seed data is already present.")
            click.echo("           Run with --reset to wipe and re-seed.")
            ds  = session.query(Dataset).filter_by(source_id=existing.id,
                                                   table_name="sample_customers").first()
            cfs = session.query(ValidationConfig).filter_by(
                dataset_id=ds.id).all() if ds else []
            return {"source_id": existing.id,
                    "dataset_id": ds.id if ds else None,
                    "config_ids": [c.id for c in cfs],
                    "config_names": [c.name for c in cfs]}

        source = DataSource(
            name              = "DataNexus Demo — CSV",
            source_type       = SourceType.csv,
            connection_string = str(csv_path),
            description       = "Sample customer CSV for CLI demo and integration testing.",
            is_active         = True,
        )
        session.add(source)
        session.flush()
        click.echo(f"  [CREATE] DataSource  id={source.id}  →  {csv_path.name}")

        dataset = Dataset(
            source_id   = source.id,
            schema_name = None,
            table_name  = "sample_customers",
            description = "20-row sample customer dataset with deliberate quality issues.",
            is_active   = True,
        )
        session.add(dataset)
        session.flush()
        click.echo(f"  [CREATE] Dataset     id={dataset.id}  →  sample_customers")

        cfg_basic = ValidationConfig(
            dataset_id        = dataset.id,
            name              = "Basic Customer Checks",
            config_yaml       = _BASIC_CONFIG_YAML,
            schedule_cron     = "0 */6 * * *",
            quality_threshold = 0.80,
            alert_on_failure  = False,
            alert_channels    = None,
            is_active         = True,
        )
        session.add(cfg_basic)
        session.flush()
        click.echo(f"  [CREATE] Config      id={cfg_basic.id}  →  'Basic Customer Checks'  "
                   f"(3 checks, threshold=80%)")

        cfg_strict = ValidationConfig(
            dataset_id        = dataset.id,
            name              = "Strict Customer Checks",
            config_yaml       = _STRICT_CONFIG_YAML,
            schedule_cron     = "0 0 * * *",
            quality_threshold = 0.90,
            alert_on_failure  = False,
            alert_channels    = None,
            is_active         = True,
        )
        session.add(cfg_strict)
        session.flush()
        click.echo(f"  [CREATE] Config      id={cfg_strict.id}  →  'Strict Customer Checks'  "
                   f"(5 checks, threshold=90%)")

        return {
            "source_id":    source.id,
            "dataset_id":   dataset.id,
            "config_ids":   [cfg_basic.id, cfg_strict.id],
            "config_names": [cfg_basic.name, cfg_strict.name],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Click command
# ─────────────────────────────────────────────────────────────────────────────

@click.command("seed")
@click.option("--reset", is_flag=True, default=False,
              help="Wipe existing seed data first, then re-seed from scratch.")
def seed_cmd(reset: bool) -> None:
    """
    Seed the database with demo data for CLI testing.

    \b
    Creates:
      data/sample_customers.csv  — 20 rows with deliberate quality issues
      data_sources               — 1 CSV source entry
      datasets                   — 1 dataset entry
      validation_configs         — 2 configs (Basic 3-check, Strict 5-check)

    Safe to run multiple times — idempotent unless --reset is passed.
    """
    click.echo()
    click.echo("DataNexus — Seed Demo Data")
    click.echo("=" * 50)

    csv_path = _PROJECT_ROOT / "data" / "sample_customers.csv"

    if reset:
        with get_db_session() as session:
            _reset(session)

    if not csv_path.exists():
        _write_csv(csv_path)
    else:
        click.echo(f"  [SKIP]   CSV already exists at {csv_path}")

    ids = _seed(csv_path)

    # ── Summary ───────────────────────────────────────────────────────────────
    config_ids = ids.get("config_ids", [])
    click.echo()
    click.echo("─" * 50)
    click.echo("  Seed complete. Try these commands next:\n")

    if len(config_ids) >= 2:
        click.echo(f"  # List all validation configs:")
        click.echo(f"  datanexus config list\n")
        click.echo(f"  # Run the Basic config (id={config_ids[0]}):")
        click.echo(f"  datanexus run {config_ids[0]}\n")
        click.echo(f"  # Run the Strict config (id={config_ids[1]}):")
        click.echo(f"  datanexus run {config_ids[1]}\n")
        click.echo(f"  # List all runs after running:")
        click.echo(f"  datanexus runs list\n")

    click.echo(f"  CSV path   : {csv_path}")
    click.echo(f"  Source id  : {ids.get('source_id')}")
    click.echo(f"  Dataset id : {ids.get('dataset_id')}")
    click.echo(f"  Config ids : {config_ids}")
    click.echo("─" * 50)
    click.echo()