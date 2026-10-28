"""``weval report``: a static report over the retained runs.

``write_report`` writes ``index.html`` into the outputs directory, leading
with the findings (every failed check with its saved judgments), then each
Treatment comparison, then each Task's reliability, plus one page per Task
and prompt variant under ``_report/tasks/`` (with one syntax-highlighted
page per packaged Task file beside it) and one page per Trial under
``_report/<run>/<trial>.html``. The index covers each Task's current
version only (``collect.split_versions``); its earlier versions, with their
findings, are at the bottom of its Task page. Notes written under
``_report/notes/`` (``weval.report.notes``) show beside the findings, Task
versions, and Trials they name. It renders only retained files, saved
analyses, saved labels, and notes: building the report never calls the
analyst or Jev, and never modifies a run directory or a note. Pages link to each other and to
retained files relatively, so the site opens from ``file://``.
"""

from datetime import datetime
from pathlib import Path

from weval import analysis
from weval.collect import (
    Comparison,
    RunSummary,
    collect_runs,
    compare_treatments,
    split_versions,
)
from weval.report.findings import FailureGroup, failure_groups, task_reliability
from weval.report.notes import DIRECTORY as NOTES_DIR
from weval.report.notes import Note, read_notes
from weval.report.pages import _task_name, render_index, render_task, render_trial
from weval.report.source import render_source

ROOT = Path(__file__).resolve().parents[3]
# Generated Task and Trial pages; collect_runs skips it because it has no
# job/ directory.
PAGES_DIR = "_report"
# Task pages, inside PAGES_DIR; no run directory name can collide with it.
TASK_PAGES_DIR = "tasks"


def write_report(outputs_dir: Path) -> Path:
    """Write the report into ``outputs_dir`` and return the index path.

    Task, file, and Trial pages left over from deleted runs are removed; no
    other file under ``outputs_dir`` is touched.
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
    current, earlier = split_versions(runs)
    current_analyses = _analyses_of(current, analyses)
    fixtures = ROOT / "tests/fixtures"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    index = outputs_dir / "index.html"
    pages_dir = outputs_dir / PAGES_DIR

    trial_pages = {
        trial.path: pages_dir / run.path.name / f"{trial.path.name}.html"
        for run in runs
        for trial in run.trials
    }
    reliability = task_reliability(current, current_analyses, fixtures)
    task_pages = {
        (row.task, row.prompt_variant): pages_dir
        / TASK_PAGES_DIR
        / f"{_task_page_name(row.task, row.prompt_variant)}.html"
        for row in reliability
    }
    file_pages: dict[Path, Path] = {}
    notes_dir = pages_dir / NOTES_DIR
    current_notes = {
        (row.task, row.prompt_variant): _version_notes(notes_dir, row.runs)
        for row in reliability
    }
    trial_notes: dict[Path, list[Note]] = {}
    for row in reliability:
        page = task_pages[row.task, row.prompt_variant]
        page.parent.mkdir(parents=True, exist_ok=True)
        task_files = _write_file_pages(
            row.runs[0].path / "task", page, _task_name(row.task)
        )
        file_pages.update(task_files)
        docs = ROOT / "docs" / f"{row.task}.md"
        earlier_versions = []
        for version_runs in earlier.get((row.task, row.prompt_variant), []):
            version_analyses = _analyses_of(version_runs, analyses)
            (version_row,) = task_reliability(version_runs, version_analyses, fixtures)
            version_groups = failure_groups(version_runs, version_analyses)
            version_notes = _version_notes(notes_dir, version_runs)
            _attach_notes(version_groups, version_notes)
            earlier_versions.append((version_row, version_groups, version_notes))
        task_notes = current_notes[row.task, row.prompt_variant]
        # A note names Trials by directory name, within its own version.
        for version_row, notes in [
            (row, task_notes),
            *((version, notes) for version, _, notes in earlier_versions),
        ]:
            for run in version_row.runs:
                for trial in run.trials:
                    trial_notes[trial.path] = [
                        n for n in notes if trial.path.name in n.trials
                    ]
        page.write_text(
            render_task(
                row,
                page_dir=page.parent,
                index=index,
                trial_pages=trial_pages,
                file_pages=task_files,
                docs=docs if docs.is_file() else None,
                notes=task_notes,
                earlier=earlier_versions,
            )
        )
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
                    task_page=task_pages[run.task, run.prompt_variant],
                    expected=expected[run.task],
                    proposals=proposals.get(trial.path.name, {}),
                    notes=trial_notes.get(trial.path, []),
                )
            )
    _remove_stale_pages(
        pages_dir,
        {*trial_pages.values(), *task_pages.values(), *file_pages.values()},
    )

    groups = failure_groups(current, current_analyses)
    for (task, prompt_variant), notes in current_notes.items():
        task_groups = [
            g for g in groups if (g.task, g.prompt_variant) == (task, prompt_variant)
        ]
        _attach_notes(task_groups, notes)
    index.write_text(
        render_index(
            current,
            current_analyses,
            groups,
            reliability,
            earlier,
            index_dir=outputs_dir,
            trial_pages=trial_pages,
            task_pages=task_pages,
            generated=datetime.now(),
        )
    )
    return index


def _write_file_pages(
    package: Path, task_page: Path, task_name: str
) -> dict[Path, Path]:
    """Write a page for each text file in ``package`` into the folder named
    after ``task_page``, and map each file to its page."""
    if not package.is_dir():
        return {}
    pages = {}
    for path in sorted(p for p in package.rglob("*") if p.is_file()):
        label = str(path.relative_to(package))
        page = task_page.with_suffix("") / f"{label}.html"
        html = render_source(
            path,
            label=label,
            page_dir=page.parent,
            task_page=task_page,
            task_name=task_name,
        )
        if html is not None:
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(html)
            pages[path] = page
    return pages


def _analyses_of(
    runs: list[RunSummary], analyses: list[tuple[Comparison, dict]]
) -> list[tuple[Comparison, dict]]:
    """The ``analyses`` whose comparisons hold ``runs``; a comparison never
    spans Task versions, so one shared run places it."""
    paths = {run.path for run in runs}
    return [
        (comparison, found)
        for comparison, found in analyses
        if any(run.path in paths for run in [*comparison.baseline, *comparison.treated])
    ]


def _version_notes(notes_dir: Path, runs: list[RunSummary]) -> list[Note]:
    """The notes for the Task version that ``runs`` share, found by the
    first recorded Task fingerprint; runs from before fingerprints read
    ``unversioned``."""
    version = next(
        (
            run.fingerprints["task"]
            for run in runs
            if (run.fingerprints or {}).get("task")
        ),
        "unversioned",
    )
    task_page_name = _task_page_name(runs[0].task, runs[0].prompt_variant)
    return read_notes(notes_dir, task_page_name, version)


def _attach_notes(groups: list[FailureGroup], notes: list[Note]) -> None:
    """Give each of one Task version's findings the notes that name its
    check."""
    for group in groups:
        group.notes = [note for note in notes if note.check == group.check]


def _task_page_name(task: str, prompt_variant: str) -> str:
    """``tasks/build/x`` as ``build-x``, with ``--<variant>`` unless default."""
    name = task.removeprefix("tasks/").replace("/", "-")
    return name if prompt_variant == "default" else f"{name}--{prompt_variant}"


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
    for page in pages_dir.rglob("*.html"):
        if page not in current:
            page.unlink()
    # Deepest first, so a folder emptied by removing its subfolders goes too.
    folders = sorted(
        (p for p in pages_dir.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for folder in folders:
        if not any(folder.iterdir()):
            folder.rmdir()
