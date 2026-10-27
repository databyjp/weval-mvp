"""``weval report``: a static site over the Task catalog and retained runs.

``write_report`` writes ``index.html`` into the outputs directory, with a
Tasks tab (each Task's definition and every Agent's latest baseline result),
a Results tab (one row per run), and a Treatments tab (Treatment runs beside
their baseline runs), plus one page per Trial under
``_report/<run>/<trial>.html``. It reads Tasks, ``agents.toml``, and retained
runs, and never modifies a run directory. Pages link to each other and to
retained files relatively, so the site opens from ``file://``.
"""

from datetime import datetime
from pathlib import Path

from weval.report.collect import collect_runs, collect_tasks, load_agents
from weval.report.pages import render_index, render_trial

ROOT = Path(__file__).resolve().parents[3]
# Generated Trial pages; collect_runs skips it because it has no job/ directory.
PAGES_DIR = "_report"


def write_report(
    outputs_dir: Path, tasks_dir: Path = ROOT / "tasks", agents_file: Path = ROOT / "agents.toml",
) -> Path:
    """Write the site into ``outputs_dir`` and return the index path.

    Trial pages left over from deleted runs are removed; no other file under
    ``outputs_dir`` is touched.
    """
    runs = collect_runs(outputs_dir)
    tasks = collect_tasks(tasks_dir)
    expected = {task.path: task.expected for task in tasks}
    Path.mkdir(outputs_dir, parents=True, exist_ok=True)
    index = outputs_dir / "index.html"
    pages_dir = outputs_dir / PAGES_DIR

    trial_pages = {
        trial.path: pages_dir / run.path.name / f"{trial.path.name}.html"
        for run in runs for trial in run.trials
    }
    for run in runs:
        for trial in run.trials:
            page = trial_pages[trial.path]
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(render_trial(run, trial, page_dir=page.parent, index=index,
                                         expected=expected.get(run.task, {})))
    _remove_stale_pages(pages_dir, set(trial_pages.values()))

    index.write_text(render_index(
        runs, tasks, load_agents(agents_file),
        index_dir=outputs_dir, trial_pages=trial_pages, generated=datetime.now(),
    ))
    return index


def _remove_stale_pages(pages_dir: Path, current: set[Path]) -> None:
    if not pages_dir.is_dir():
        return
    for page in pages_dir.glob("*/*.html"):
        if page not in current:
            page.unlink()
    for run_dir in pages_dir.iterdir():
        if run_dir.is_dir() and not any(run_dir.iterdir()):
            run_dir.rmdir()
