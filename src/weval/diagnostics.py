"""Facts about how a Trial reached its result, read from its retained logs.

Diagnostics explain check results; they never change them. They are
computed on the host each time they are read, from Harbor's
``agent/trajectory.json`` (one format for every harness), the run's
``treatment/`` copy, and ``verifier/application.log``, so retained Trials get
them too. Nothing is written.
"""

import json
import re
from collections.abc import Callable
from pathlib import Path

# External URLs in a tool call's arguments. A URL's host must contain a dot,
# which excludes Compose service names such as weaviate:8080 and localhost;
# loopback addresses are excluded separately. Backslashes end a URL because
# arguments are matched in their JSON encoding. A trailing ; , or . ends the
# shell command or sentence, not the URL.
URL = re.compile(
    r"https?://(?!127\.0\.0\.1|0\.0\.0\.0)[^\s/'\"`:\\]+\.[^\s/'\"`:\\]+[^\s'\"`<>)\]}\\]*(?<![;,.])"
)
# A shell variable assigned a URL, as in B=https://host/docs; curl $B/page.md
SHELL_URL_ASSIGNMENT = re.compile(r"\b([A-Za-z_]\w*)=(https?://[^\s;&|'\"`\\]+)")


def urls_in(arguments: str) -> list[str]:
    """Return the external URLs in a tool call's JSON-encoded arguments, in order.

    A shell variable assigned a URL in the same arguments is expanded where
    it is used (``$B/page.md`` or ``${B}/page.md``), and the assignment alone
    is not listed. Other variables, such as a loop counter in
    ``...&page=$page``, stay unexpanded.
    """
    values = dict(SHELL_URL_ASSIGNMENT.findall(arguments))
    arguments = SHELL_URL_ASSIGNMENT.sub(r"\1=", arguments)
    for name, value in values.items():
        # A function replacement, so backslashes in the URL are not escapes.
        arguments = re.sub(
            rf"\$(?:{name}\b|\{{{name}\}})", lambda _, url=value: url, arguments
        )
    return URL.findall(arguments)


# The Weaviate Python client numbers its deprecation warnings ("Dep024: ...").
# Other libraries' warnings (authlib's, in every Trial) are left out.
DEPRECATION = re.compile(r"\bDep\d{3}:[^\n]*")


def diagnose(
    trial_dir: Path,
    expected: dict[str, Callable[[dict], str | None]],
    snapshot: dict,
    results: list[dict],
) -> dict:
    """Diagnostics for one Trial's check ``results``, given its Task's
    ``check.py`` ``EXPECTED`` (empty when the Task defines none).

    - ``treatment_used``: ``None`` for a baseline, else whether a Treatment
      skill loaded and which of its files a tool call named (``files_named``;
      a glob such as ``*.md`` reads files without naming them).
    - ``expected_value_seen``: for each failed check in ``results`` that
      ``expected`` gives a value for, whether that value appeared in
      what the agent was shown: tool results and injected messages, not its
      own output.
    - ``deprecations_seen``: Weaviate deprecation warnings the agent was
      shown; ``deprecations_logged``: those in ``verifier/application.log``.

    The trajectory-based fields are ``None`` when the Trial has no
    ``agent/trajectory.json``.
    """
    shown, called = _trajectory_text(trial_dir / "agent/trajectory.json")
    log = trial_dir / "verifier/application.log"
    return {
        "treatment_used": _treatment_used(
            trial_dir.parents[1] / "treatment/skills", called
        ),
        "expected_value_seen": None
        if shown is None
        else _expected_value_seen(expected, snapshot, results, shown),
        "deprecations_seen": None if shown is None else _deprecations(shown),
        "deprecations_logged": _deprecations([log.read_text(errors="replace")])
        if log.exists()
        else [],
    }


def _trajectory_text(path: Path) -> tuple[list[str] | None, list[str] | None]:
    """What the agent was shown (tool results and non-agent messages, such as
    an injected skill) and what it called (tool names with arguments)."""
    if not path.exists():
        return None, None
    shown, called = [], []
    for step in json.loads(path.read_text())["steps"]:
        if step.get("source") != "agent":
            shown.append(str(step.get("message") or ""))
        for result in (step.get("observation") or {}).get("results", []):
            shown.append(str(result.get("content") or ""))
        for call in step.get("tool_calls") or []:
            called.append(
                f"{call['function_name']} {json.dumps(call.get('arguments'))}"
            )
    return shown, called


def _treatment_used(skills: Path, called: list[str] | None) -> dict | None:
    if not skills.is_dir() or called is None:
        return None
    names = [path.name for path in skills.iterdir() if (path / "SKILL.md").exists()]
    # Claude Code loads a skill with its Skill tool; Pi reads the SKILL.md.
    skill_tool_called = any(
        text.startswith("Skill ")
        and json.loads(text[len("Skill ") :]).get("skill") in names
        for text in called
    )
    skill_md_read = any(f"{name}/SKILL.md" in text for text in called for name in names)
    loaded = skill_tool_called or skill_md_read
    files = sorted(
        str(path.relative_to(skills))
        for path in skills.rglob("*")
        if path.is_file()
        and path.name != "SKILL.md"
        and any(path.name in text for text in called)
    )
    return {"skill_loaded": loaded, "files_named": files}


def _expected_value_seen(
    expected: dict, snapshot: dict, results: list[dict], shown: list[str]
) -> list[dict]:
    seen = []
    for result in results:
        if result["passed"] or result["name"] not in expected:
            continue
        try:
            value = expected[result["name"]](snapshot)
        except (KeyError, TypeError):
            # An error snapshot, or a fact the snapshot could not record.
            value = None
        if value is None:
            continue
        # Exact value, so 4.24.1 matches "v4.24.1" but neither 4.24.10 nor 14.24.1.
        pattern = re.compile(rf"(?<![\d.]){re.escape(value)}(?!\.?\d)")
        seen.append(
            {
                "check": result["name"],
                "expected": value,
                "seen": any(pattern.search(text) for text in shown),
            }
        )
    return seen


def _deprecations(texts: list[str]) -> list[str]:
    return sorted(
        {
            match.group(0).strip()[:200]
            for text in texts
            for match in DEPRECATION.finditer(text)
        }
    )
