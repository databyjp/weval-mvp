"""Every Task has a page at docs/tasks/<stage>/<scenario>.md whose frontmatter
states its motivation and whose checks table matches its check.py."""

import importlib.util
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
TASK_DIRS = sorted(p.parent for p in ROOT.glob("tasks/*/*/check.py"))
# A checks-table row: | `check-id` | REQUIRED | ...
CHECK_ROW = re.compile(r"^\| `([a-z0-9-]+)` \| (REQUIRED|PREFERRED) \|", re.MULTILINE)


def task_id(task_dir: Path) -> str:
    return f"{task_dir.parent.name}/{task_dir.name}"


def frontmatter(page: str) -> dict:
    """Return the YAML between the opening and closing ``---`` lines, or {}."""
    match = re.match(r"---\n(.*?)\n---\n", page, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def check_tiers(task_dir: Path) -> dict[str, str]:
    spec = importlib.util.spec_from_file_location(f"{task_dir.name}_check", task_dir / "check.py")
    assert spec and spec.loader
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    return {
        function.__name__.replace("_", "-"): tier
        for tier, functions in (("REQUIRED", check.REQUIRED), ("PREFERRED", check.PREFERRED))
        for function in functions
    }


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=task_id)
def test_task_page_matches_task(task_dir):
    page_path = ROOT / "docs/tasks" / f"{task_id(task_dir)}.md"
    assert page_path.exists(), f"{task_id(task_dir)} has no page at {page_path.relative_to(ROOT)}"
    page = page_path.read_text()

    assert frontmatter(page).get("motivation"), "the page's frontmatter states a motivation"

    documented = dict(CHECK_ROW.findall(page))
    assert documented == check_tiers(task_dir), "the checks table lists check.py's checks and tiers"
