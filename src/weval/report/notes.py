"""Notes people and agents write about a Task version's results.

A note is a Markdown file under the report's pages, which ``weval report``
reads and never writes or deletes (it removes only stale ``.html`` pages)::

    _report/notes/<task page name>/<task version>/<name>.md

The Task page name is the Task page's file name without ``.html``, such as
``build-ecommerce-search``, and the Task version is the ``task``
fingerprint in the runs' ``weval.json``, such as ``35f56f59e981``. The note
starts with a header; every field is optional::

    ---
    author: claude-code
    date: 2026-10-28
    check: weaviate-server-version
    trials: [task__ZYLBTdY, task__JrtcPP6]
    ---

A note with a ``check`` shows under that check's finding, a note naming
``trials`` shows on each of those Trial pages, and every note shows on its
Task page beside the version it belongs to.
"""

from dataclasses import dataclass
from pathlib import Path

DIRECTORY = "notes"


@dataclass(frozen=True)
class Note:
    """One note file: its header fields and Markdown body."""

    path: Path
    author: str | None
    date: str | None
    check: str | None
    trials: tuple[str, ...]
    body: str


def read_notes(notes_dir: Path, task_page_name: str, task_version: str) -> list[Note]:
    """The notes for one Task, prompt variant, and Task version, by date and
    then file name; none when the folder does not exist."""
    folder = notes_dir / task_page_name / task_version
    notes = [_parse(path) for path in sorted(folder.glob("*.md"))]
    return sorted(notes, key=lambda note: note.date or "")


def _parse(path: Path) -> Note:
    text = path.read_text()
    fields: dict[str, str] = {}
    lines = text.splitlines()
    # The header sits between the first two "---" lines, the first at the top.
    rules = [i for i, line in enumerate(lines) if line.strip() == "---"]
    if rules[:1] == [0] and len(rules) > 1:
        end = rules[1]
        for line in lines[1:end]:
            key, _, value = line.partition(":")
            # YAML-style comments: "author: me  # or a person".
            fields[key.strip()] = value.split(" #")[0].strip()
        text = "\n".join(lines[end + 1 :])
    trials = fields.get("trials", "").strip("[]")
    return Note(
        path=path,
        author=fields.get("author") or None,
        date=fields.get("date") or None,
        check=fields.get("check") or None,
        trials=tuple(t.strip() for t in trials.split(",") if t.strip()),
        body=text.strip(),
    )
