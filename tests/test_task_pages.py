"""Every Task states its motivation, in one of two places while Tasks move
from pages to their own files:

- ``task.toml``'s ``[metadata] motivation``, with no page, and a docstring on
  every check, which is then the only statement of what it scores;
- a page at docs/tasks/<stage>/<scenario>.md whose frontmatter states the
  motivation and whose checks table matches its check.py.
"""

import importlib.util
import re
import tomllib
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


def check_functions(task_dir: Path) -> dict[str, tuple[str, object]]:
    """Map each check ID to its tier and function."""
    spec = importlib.util.spec_from_file_location(f"{task_dir.name}_check", task_dir / "check.py")
    assert spec and spec.loader
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    return {
        function.__name__.replace("_", "-"): (tier, function)
        for tier, functions in (("REQUIRED", check.REQUIRED), ("PREFERRED", check.PREFERRED))
        for function in functions
    }


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=task_id)
def test_task_states_its_motivation_and_checks(task_dir):
    page_path = ROOT / "docs/tasks" / f"{task_id(task_dir)}.md"
    metadata = tomllib.loads((task_dir / "task.toml").read_text()).get("metadata") or {}
    if "motivation" in metadata:
        assert metadata["motivation"].strip(), "task.toml's [metadata] motivation is not blank"
        assert not page_path.exists(), f"the spec is in the Task's files; remove {page_path.relative_to(ROOT)}"
        undocumented = [name for name, (_, function) in check_functions(task_dir).items() if not function.__doc__]
        assert not undocumented, f"every check has a docstring; missing for {undocumented}"
        return

    assert page_path.exists(), f"{task_id(task_dir)} has no page at {page_path.relative_to(ROOT)}"
    page = page_path.read_text()

    assert frontmatter(page).get("motivation"), "the page's frontmatter states a motivation"

    documented = dict(CHECK_ROW.findall(page))
    tiers = {name: tier for name, (tier, _) in check_functions(task_dir).items()}
    assert documented == tiers, "the checks table lists check.py's checks and tiers"
