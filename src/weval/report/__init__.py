"""``weval report``: a static report over the retained runs.

``write_report`` writes ``index.html`` into the outputs directory, leading
with the findings (every failed check with its saved judgments), then each
Treatment comparison, then each Task's reliability, plus one page per Trial
under ``_report/<run>/<trial>.html``. It renders only retained files, saved
analyses, and saved labels: building the report never calls the analyst or
Jev, and never modifies a run directory. Pages link to each other and to
retained files relatively, so the site opens from ``file://``.
"""

from datetime import datetime
from pathlib import Path

from weval import analysis
from weval.collect import Comparison, collect_runs, compare_treatments
from weval.report.findings import failure_groups, task_reliability
from weval.report.pages import render_index, render_trial

ROOT = Path(__file__).resolve().parents[3]
# Generated Trial pages; collect_runs skips it because it has no job/ directory.
PAGES_DIR = "_report"


def write_report(outputs_dir: Path) -> Path:
    """Write the report into ``outputs_dir`` and return the index path.

    Trial pages left over from deleted runs are removed; no other file under
    ``outputs_dir`` is touched.
    """
    runs = collect_runs(outputs_dir)
    expected = {task: _expected(task) for task in {run.task for run in runs}}
    analyses = [
        (
            comparison,
            analysis.analyse(
                comparison, expected[comparison.task], outputs_dir, call=False
            ),
        )
        for comparison in compare_treatments(runs)
    ]
    proposals = _trial_proposals(analyses)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    index = outputs_dir / "index.html"
    pages_dir = outputs_dir / PAGES_DIR

    trial_pages = {
        trial.path: pages_dir / run.path.name / f"{trial.path.name}.html"
        for run in runs
        for trial in run.trials
    }
    for run in runs:
        for trial in run.trials:
            page = trial_pages[trial.path]
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(
                render_trial(
                    run,
                    trial,
                    page_dir=page.parent,
                    index=index,
                    expected=expected[run.task],
                    proposals=proposals.get(trial.path.name, {}),
                )
            )
    _remove_stale_pages(pages_dir, set(trial_pages.values()))

    index.write_text(
        render_index(
            runs,
            analyses,
            failure_groups(runs, analyses),
            task_reliability(runs, analyses, ROOT / "tests/fixtures"),
            index_dir=outputs_dir,
            trial_pages=trial_pages,
            generated=datetime.now(),
        )
    )
    return index


def _expected(task: str) -> dict:
    """The Task's ``check.py`` ``EXPECTED``, for diagnostics; empty when the
    Task or its ``check.py`` is missing or broken, so a bad Task cannot break
    the report."""
    # Imported here to avoid importing Harbor (via weval.run) at module load.
    from weval.rescore import load_check

    try:
        return getattr(load_check(ROOT / task), "EXPECTED", {})
    except Exception:  # noqa: BLE001  A broken Task must not break the report.
        return {}


def _trial_proposals(
    analyses: list[tuple[Comparison, dict]],
) -> dict[str, dict[str, list[dict]]]:
    """Saved class proposals per Trial name and check, for the Trial pages:
    the analyst's patterns and the rule's, each ``{"class", "who", "reason"}``."""
    proposals: dict[str, dict[str, list[dict]]] = {}

    def add(trial: str, check: str, row: dict) -> None:
        rows = proposals.setdefault(trial, {}).setdefault(check, [])
        if row not in rows:
            rows.append(row)

    for _, found in analyses:
        for pattern in ((found.get("analysis") or {}).get("patterns")) or []:
            who = f"analyst ({found.get('model')})"
            for trial in pattern["trials"]:
                for check in pattern["checks"]:
                    add(
                        trial,
                        check,
                        {
                            "class": pattern["class"],
                            "who": who,
                            "reason": pattern["reason"],
                        },
                    )
        for row in found["rule"]:
            add(
                row["trial"],
                row["check"],
                {"class": row["class"], "who": "rule", "reason": row["reason"]},
            )
    return proposals


def _remove_stale_pages(pages_dir: Path, current: set[Path]) -> None:
    if not pages_dir.is_dir():
        return
    for page in pages_dir.glob("*/*.html"):
        if page not in current:
            page.unlink()
    for run_dir in pages_dir.iterdir():
        if run_dir.is_dir() and not any(run_dir.iterdir()):
            run_dir.rmdir()
