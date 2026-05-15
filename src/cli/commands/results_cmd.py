"""
src/cli/commands/results_cmd.py
================================
`runs` command group with two sub-commands:

  datanexus runs list [--limit N]
      Shows a table of recent ValidationRuns: id, config name,
      status, quality score, triggered_by, started_at.

  datanexus runs show <run-id>
      Shows the full run card + a detailed per-check results table
      for one specific run.
"""

import sys
from pathlib import Path

import click

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.database import get_db_session
from src.database.models import ValidationRun, ValidationResult, ValidationConfig
from src.cli.formatting import (
    print_table, print_run_card,
    status_label, severity_label, score_bar,
)


# ─────────────────────────────────────────────────────────────────────────────
# Group
# ─────────────────────────────────────────────────────────────────────────────

@click.group("runs")
def runs_group() -> None:
    """List and inspect validation runs."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# datanexus runs list
# ─────────────────────────────────────────────────────────────────────────────

@runs_group.command("list")
@click.option("--limit", default=20, show_default=True, type=int,
              help="Maximum number of runs to display (most recent first).")
@click.option("--config-id", default=None, type=int,
              help="Filter runs by a specific config id.")
def runs_list(limit: int, config_id: int) -> None:
    """
    List recent validation runs.

    \b
    Examples:
      datanexus runs list
      datanexus runs list --limit 5
      datanexus runs list --config-id 1
    """
    try:
        with get_db_session() as session:
            query = session.query(ValidationRun).order_by(ValidationRun.id.desc())
            if config_id is not None:
                query = query.filter_by(config_id=config_id)
            runs = query.limit(limit).all()

            if not runs:
                click.echo("\n  No validation runs found.")
                click.echo("  Run `datanexus run <config-id>` to create one.\n")
                return

            rows = []
            for r in runs:
                cfg_name = r.config.name if r.config else "—"
                score    = f"{r.quality_score:.1f}" if r.quality_score is not None else "—"
                started  = r.started_at.strftime("%Y-%m-%d %H:%M") if r.started_at else "—"
                rows.append([
                    r.id,
                    r.config_id or "—",
                    cfg_name[:35],   # truncate long names
                    status_label(r.status.value if r.status else "unknown"),
                    score,
                    r.triggered_by or "—",
                    started,
                ])

        print_table(
            headers=["ID", "Config ID", "Config Name", "Status", "Score", "Triggered By", "Started At"],
            rows=rows,
            title=f"Recent Validation Runs  (showing {len(rows)})",
        )
        click.echo()

    except Exception as exc:
        click.echo(f"\n  Error querying runs: {exc}\n")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# datanexus runs show <run-id>
# ─────────────────────────────────────────────────────────────────────────────

@runs_group.command("show")
@click.argument("run_id", type=int)
def runs_show(run_id: int) -> None:
    """
    Show full details for one validation run.

    RUN_ID is the integer id from the validation_runs table.
    Use `datanexus runs list` to see available run ids.

    \b
    Examples:
      datanexus runs show 1
      datanexus runs show 42
    """
    try:
        with get_db_session() as session:
            run = session.query(ValidationRun).filter_by(id=run_id).first()
            if run is None:
                click.echo(f"\n  Error: No ValidationRun with id={run_id} found.")
                click.echo("  Run `datanexus runs list` to see available run ids.\n")
                sys.exit(1)

            cfg     = run.config
            results = (
                session.query(ValidationResult)
                .filter_by(run_id=run_id)
                .order_by(ValidationResult.id)
                .all()
            )

            # ── Run header card ───────────────────────────────────────────────
            run_dict = {
                "id":            run.id,
                "status":        run.status.value if run.status else "unknown",
                "quality_score": run.quality_score,
                "config_id":     run.config_id,
                "config_name":   cfg.name if cfg else None,
                "triggered_by":  run.triggered_by,
                "started_at":    run.started_at,
                "finished_at":   run.finished_at,
                "error_message": run.error_message,
            }
            print_run_card(run_dict)

            # ── Per-check results table ───────────────────────────────────────
            if not results:
                click.echo("  No check results recorded for this run.\n")
                return

            rows = []
            for r in results:
                failing = r.failing_rows if r.failing_rows is not None else 0
                total   = r.total_rows   if r.total_rows   is not None else 0
                ratio   = f"{failing}/{total}" if total else "—"

                rows.append([
                    r.id,
                    r.check_name,
                    r.check_type,
                    r.column_name or "—",
                    status_label(r.status.value if r.status else "unknown"),
                    severity_label(r.severity.value if r.severity else "?"),
                    ratio,
                    (r.error_message[:40] + "…") if r.error_message else "—",
                ])

            print_table(
                headers=["ID", "Check Name", "Type", "Column",
                         "Status", "Severity", "Fail/Total", "Error"],
                rows=rows,
                title=f"Check Results  (run #{run_id})",
            )

            # ── Counts summary ────────────────────────────────────────────────
            statuses = [r.status.value for r in results if r.status]
            n_pass  = statuses.count("pass")
            n_fail  = statuses.count("fail")
            n_error = statuses.count("error")
            click.echo(f"  Totals: {n_pass} passed  |  {n_fail} failed  |  {n_error} error\n")

    except SystemExit:
        raise
    except Exception as exc:
        click.echo(f"\n  Error: {exc}\n")
        sys.exit(1)
