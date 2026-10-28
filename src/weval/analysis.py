"""An LLM analyst's reading of one Treatment comparison across Agents,
checked against the facts it was given.

The analyst never reads transcripts. It gets ``facts()``: each arm's pass
counts and mean usage, whether the Treatment helped, hurt, or left unchanged
each Agent's pass rate, and every failed check with its Agent, failure
message, diagnostics, and saved Jev labels. It
answers in a fixed structure: a one-sentence result, failure patterns (each
with its checks, Trial IDs, evidence, and a proposed class from ``CLASSES``),
caveats, and open questions. ``verify()`` rejects an answer that cites an
unknown Trial or check, states a number the facts do not contain, or leaves
a failed required check out of every pattern; the analyst is asked again with
the problems, and an answer still rejected after ``ATTEMPTS`` is saved as
rejected, never edited.

``propose_class()`` is a hand-coded rule over the same facts. Its proposals
are not shown to the analyst; where both name a class for the same failed
check and they differ, the disagreement is listed for a person to decide.

Analyses explain results; they never change a score. Each is saved in
``<outputs>/_analysis/<comparison>.json``, keyed by a hash of the request, so
a repeat costs nothing and any change to the facts, prompt, or model asks
again. Calls go to OpenRouter's Anthropic-compatible endpoint and need
``OPENROUTER_API_KEY``. The API accepts no sampling parameters, so
repeatability rests on the pinned model, ``PROMPT_VERSION``, and the cache.
"""

import difflib
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

import anthropic

from weval import diagnostics, labels
from weval.collect import SCORED, Comparison, TrialSummary, mean_usage, median_change

API = "https://openrouter.ai/api"
MODEL = "anthropic/claude-sonnet-5.5"
KEY_VAR = "OPENROUTER_API_KEY"
# Raise when SYSTEM, SCHEMA, or the shape of facts() changes meaning.
PROMPT_VERSION = "4"
ATTEMPTS = 3
DIRECTORY = "_analysis"
# Check failure messages are capped one by one; the analyst needs what was
# checked and what was found, not whole submitted values.
NOTES_CHARS = 400
# AGENTS.md's failure classes.
CLASSES = (
    "agent gap",
    "Weaviate gap",
    "scorer bug",
    "Task defect",
    "infrastructure failure",
)
UNCLASSIFIED = "unclassified"
# Pages Weaviate publishes: its docs and sites, and its GitHub organisation.
WEAVIATE_PAGE = re.compile(
    r"^https?://(([^/]+\.)?weaviate\.io(/|$)|github\.com/weaviate/)"
)
# Numbers as the analyst writes them: integers, decimals, and versions.
NUMBER = re.compile(r"\d+(?:\.\d+)*")

SYSTEM = """\
You analyse one comparison from weval, which runs Weaviate coding Tasks against coding agents. A Treatment \
gives the agent extra skills, replaces the Task's prompt (treatment_prompt_diff shows the change), or both; \
the baseline arm runs without one. Several agents, each a harness and a model, \
ran both arms, so the comparison asks whether the Treatment helps across agents. You get computed facts as \
JSON: each arm's pass counts and mean usage per Trial over all agents; for each agent, its pass counts in \
both arms and whether the Treatment helped, hurt, or left its pass rate unchanged; the median of the agents' \
usage changes; and every failed check of every Trial, with the Trial's agent. A failed check carries its \
failure message; for some checks, the \
value the check expected and whether that value appeared in what the agent was shown; and Jev labels, a \
classifier's reading of the trace steps that bear on the failed choice: why the agent made it (no_lookup, \
followed_source, ignored_current_practice, considered_and_rejected, environment_forced, or \
no_trace_evidence) and which source it took the value from (a URL, a Treatment file, a search, or \
own-knowledge), each with a confidence from 0 to 1.

Answer with:
- result: one sentence on what the Treatment changed, with both arms' pass counts and how many agents it \
helped and hurt.
- patterns: the failed checks grouped into failure patterns. Each names its checks, the IDs of the Trials \
that show it, the evidence from the facts, a proposed class, and the reason for that class.
- caveats: limits on what the facts support, such as one Trial per agent and arm, or low label confidence.
- open_questions: what a person must check outside these facts, such as what a docs page says.

Classes:
- agent gap: the agent missed something it could have discovered.
- Weaviate gap: the product or its docs led the agent astray.
- scorer bug: the check misjudged a correct solution.
- Task defect: the prompt or workspace hid or contradicted a scored constraint.
- infrastructure failure: the environment prevented a valid outcome.

A failed check is a finding about the agent or Weaviate, not a defect to remove. Propose scorer bug or Task \
defect only when the facts show the check or the prompt is wrong. Use only the facts given. Write each \
number exactly as the facts give it, and cite Trials by their exact IDs. Put anything that depends on \
knowledge outside the facts in open_questions. Every failed required check must belong to a pattern."""

_TEXT = {"type": "string"}
_TEXTS = {"type": "array", "items": _TEXT}
SCHEMA = {
    "type": "object",
    "properties": {
        "result": _TEXT,
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "summary": _TEXT,
                    "checks": _TEXTS,
                    "trials": _TEXTS,
                    "evidence": _TEXT,
                    "class": {"type": "string", "enum": list(CLASSES)},
                    "reason": _TEXT,
                },
                "required": [
                    "summary",
                    "checks",
                    "trials",
                    "evidence",
                    "class",
                    "reason",
                ],
                "additionalProperties": False,
            },
        },
        "caveats": _TEXTS,
        "open_questions": _TEXTS,
    },
    "required": ["result", "patterns", "caveats", "open_questions"],
    "additionalProperties": False,
}


def facts(comparison: Comparison, expected: dict) -> dict:
    """The computed facts the analyst is given for ``comparison``, whose
    Task's ``check.py`` ``EXPECTED`` is ``expected`` (empty when it has none).

    Only scored Trials are included. ``agents`` has one row per compared
    Agent with its pass counts and ``change`` (``AgentChange``), and
    ``agent_changes`` counts the rows by change. Usage changes are the median
    over Agents of each Agent's change, in whole percent, so one costly model
    does not set them. A failure's ``expected`` is ``None`` when ``EXPECTED``
    has no entry for its check; otherwise its ``value`` is ``None`` when the
    snapshot gave none, and its ``seen`` is ``None`` when the Trial has no
    trajectory.
    """
    readme = _readme(comparison.treated[0].path / "treatment/README.md")
    by_agent = comparison.by_agent()
    usage_changes = {}
    for attribute in ("cost_usd", "uncached_input", "turns"):
        change = median_change(by_agent, attribute)
        usage_changes[attribute] = None if change is None else round(100 * change)
    return {
        "task": comparison.task,
        "treatment": comparison.treatment,
        "treatment_readme": readme,
        "treatment_prompt_diff": _prompt_diff(comparison),
        "versions": {
            "task": comparison.task_version,
            "check": comparison.check_version,
            "treatment": comparison.treatment_version,
        },
        "arms": {
            "baseline": _arm(comparison.baseline, expected),
            "treatment": _arm(comparison.treated, expected),
        },
        "agents": [
            {
                "agent": row.agent,
                "baseline": _counts(row.baseline),
                "treatment": _counts(row.treated),
                "change": row.change,
            }
            for row in by_agent
        ],
        "agent_changes": dict(Counter(row.change or "not scored" for row in by_agent)),
        "unpaired_agents": comparison.unpaired,
        "median_usage_change_percent": usage_changes,
    }


def _counts(trials: list[TrialSummary]) -> dict:
    scored = _scored(trials)
    return {
        "scored": len(scored),
        "passed": sum(t.status == "passed" for t in scored),
    }


def _scored(trials: list[TrialSummary]) -> list[TrialSummary]:
    return [t for t in trials if t.status in SCORED]


def propose_class(failure: dict) -> dict:
    """The rule's proposed class for one failed check from ``facts()``, with
    its reason: ``{"class", "reason"}``. The class is one of ``CLASSES`` or
    ``unclassified``, which leaves the failure to a person."""
    expected, source = (
        failure["expected"],
        (failure["labels"] or {}).get("answer_source") or {},
    )
    if failure["error_stage"]:
        return {
            "class": "infrastructure failure",
            "reason": f"snapshot error at stage {failure['error_stage']}",
        }
    if expected is None:
        return {"class": UNCLASSIFIED, "reason": "the check defines no expected value"}
    if expected["value"] is None:
        return {
            "class": "infrastructure failure",
            "reason": "the verifier recorded no expected value",
        }
    if expected["seen"] is None:
        return {
            "class": UNCLASSIFIED,
            "reason": "no trajectory to say what the agent was shown",
        }
    if expected["seen"]:
        return {
            "class": "agent gap",
            "reason": f"the agent was shown {expected['value']} and answered otherwise",
        }
    if WEAVIATE_PAGE.match(str(source.get("choice", ""))):
        return {
            "class": "Weaviate gap",
            "reason": f"{expected['value']} was not in what the agent was shown; Jev labels the source "
            f"{source['choice']} (confidence {source['confidence']})",
        }
    return {
        "class": UNCLASSIFIED,
        "reason": f"{expected['value']} was not in what the agent was shown, and no Weaviate page is its labelled source",
    }


def verify(answer: dict, given: dict) -> list[str]:
    """Problems that make ``answer`` unusable against the ``given`` facts;
    empty when it passes."""
    failed = _failures(given)
    problems = []
    for i, pattern in enumerate(answer["patterns"]):
        if pattern["class"] not in CLASSES:
            problems.append(
                f"pattern {i + 1}: class {pattern['class']!r} is not one of {list(CLASSES)}"
            )
        for check in pattern["checks"]:
            if check not in {name for (_, name) in failed}:
                problems.append(f"pattern {i + 1}: {check!r} is not a failed check")
        for trial in pattern["trials"]:
            if not any((trial, check) in failed for check in pattern["checks"]):
                problems.append(
                    f"pattern {i + 1}: Trial {trial!r} did not fail any of the pattern's checks"
                )

    covered = {
        (trial, check)
        for p in answer["patterns"]
        for trial in p["trials"]
        for check in p["checks"]
    }
    for (trial, check), failure in failed.items():
        if failure["required"] and (trial, check) not in covered:
            problems.append(
                f"failed required check {check!r} of Trial {trial!r} is in no pattern"
            )

    # Identifiers carry digits of their own, so they are removed first.
    names = sorted(
        {trial for trial, _ in failed}
        | {t["id"] for arm in given["arms"].values() for t in arm["trials"]},
        key=len,
        reverse=True,
    )
    known = set(NUMBER.findall(json.dumps(given)))
    texts = [
        answer["result"],
        *answer["caveats"],
        *answer["open_questions"],
        *(
            p[key]
            for p in answer["patterns"]
            for key in ("summary", "evidence", "reason")
        ),
    ]
    for text in texts:
        # Thousands separators: 83,554 is the facts' 83554.
        text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
        for name in names:
            text = text.replace(name, "")
        unknown = sorted(set(NUMBER.findall(text)) - known)
        if unknown:
            problems.append(
                f"numbers not in the facts: {', '.join(unknown)} (in {text[:80]!r})"
            )
    return problems


def cross_check(answer: dict | None, given: dict) -> tuple[list[dict], list[dict]]:
    """The rule's proposal for every failed check in ``given``, and where an
    accepted ``answer`` puts the same failed check in a pattern of another
    class. Each proposal is ``{"trial", "check", "class", "reason"}``; each
    disagreement adds the pattern's ``analyst`` class to it."""
    proposals = [
        {"trial": trial, "check": check, **propose_class(failure)}
        for (trial, check), failure in _failures(given).items()
    ]
    disagreements = []
    for proposal in proposals:
        if proposal["class"] == UNCLASSIFIED or answer is None:
            continue
        for pattern in answer["patterns"]:
            if (
                proposal["trial"] in pattern["trials"]
                and proposal["check"] in pattern["checks"]
                and pattern["class"] != proposal["class"]
            ):
                disagreements.append({**proposal, "analyst": pattern["class"]})
    return proposals, disagreements


def analyse(
    comparison: Comparison, expected: dict, outputs_dir: Path, *, call: bool = True
) -> dict:
    """The analysis of ``comparison``, whose Task's ``EXPECTED`` is
    ``expected``, saved under ``outputs_dir``.

    Returns ``{"analysis", "model", "problems", "rule", "disagreements",
    "note"}``. ``analysis`` is the accepted answer, or ``None`` when none is
    saved for the current facts or the last answer was rejected, in which
    case ``problems`` lists what ``verify`` found in it. ``rule`` and
    ``disagreements`` come from ``cross_check`` and are computed whether or
    not the analyst is called. With ``call`` false, or without the API key,
    only a saved analysis is returned and ``note`` says why there is none.
    A failed request is reported in ``note`` rather than raised.
    """
    given = facts(comparison, expected)
    body = {
        "model": MODEL,
        "max_tokens": 16000,
        "system": SYSTEM,
        "messages": [
            {
                "role": "user",
                "content": f"Facts:\n```json\n{json.dumps(given, indent=1)}\n```",
            }
        ],
        "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
    }
    digest = hashlib.sha256(
        json.dumps({"prompt_version": PROMPT_VERSION, **body}, sort_keys=True).encode()
    ).hexdigest()
    saved_file = outputs_dir / DIRECTORY / f"{_name(comparison)}.json"
    saved = json.loads(saved_file.read_text()) if saved_file.exists() else None

    note = None
    if saved and saved["request_sha256"] == digest:
        result = saved
    elif not comparison.baseline:
        result, note = None, "not analysed (no baseline run)"
    elif not (call and (key := os.environ.get(KEY_VAR))):
        result, note = (
            None,
            f"not analysed ({'not requested' if not call else f'{KEY_VAR} is not set'})",
        )
    else:
        try:
            result = _ask(body, given, key)
        except anthropic.APIError as error:
            result, note = None, f"analysis request failed: {error}"
        else:
            result = {
                "request_sha256": digest,
                "prompt_version": PROMPT_VERSION,
                "facts": given,
                **result,
            }
            saved_file.parent.mkdir(exist_ok=True)
            saved_file.write_text(json.dumps(result, indent=1))

    answer = (result or {}).get("analysis")
    rule, disagreements = cross_check(answer, given)
    return {
        "analysis": answer,
        "model": (result or {}).get("model"),
        "problems": (result or {}).get("problems", []),
        "rule": rule,
        "disagreements": disagreements,
        "note": note,
    }


def _ask(body: dict, given: dict, key: str) -> dict:
    """Ask until an answer passes ``verify`` or ``ATTEMPTS`` run out; each
    retry appends the rejected answer and its problems, so the conversation
    only grows."""
    messages = list(body["messages"])
    responses, problems = [], []
    for _ in range(ATTEMPTS):
        response = _post({**body, "messages": messages}, key)
        responses.append(response)
        text = next(
            (block["text"] for block in response["content"] if block["type"] == "text"),
            "",
        )
        try:
            answer = json.loads(text)
            problems = verify(answer, given)
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            answer, problems = (
                None,
                [
                    f"stop reason {response.get('stop_reason')}; not an answer in the schema: {error}"
                ],
            )
        if not problems:
            return {
                "model": response.get("model"),
                "analysis": answer,
                "problems": [],
                "responses": responses,
            }
        messages += [
            {"role": "assistant", "content": response["content"]},
            {
                "role": "user",
                "content": "These problems make the answer unusable:\n- "
                + "\n- ".join(problems)
                + "\nAnswer again, fixing them.",
            },
        ]
    return {
        "model": responses[-1].get("model"),
        "analysis": None,
        "problems": problems,
        "responses": responses,
    }


def _post(body: dict, key: str) -> dict:
    # An explicit token stops the SDK reading ANTHROPIC_API_KEY, which must
    # not be sent to OpenRouter. The SDK retries 429 and 5xx itself.
    client = anthropic.Anthropic(base_url=API, auth_token=key)
    return client.messages.create(**body).to_dict()


def _arm(runs: list, expected: dict) -> dict:
    trials = [(run.agent, t) for run in runs for t in run.scored]
    scored = [t for _, t in trials]

    def mean(attribute: str, digits: int | None) -> float | None:
        value = mean_usage(scored, attribute)
        return None if value is None else round(value, digits)

    return {
        "runs": [run.path.name for run in runs],
        "scored": len(scored),
        "passed": sum(t.status == "passed" for t in scored),
        "mean_cost_usd": mean("cost_usd", 3),
        "mean_uncached_input_tokens": mean("uncached_input", None),
        "mean_turns": mean("turns", 1),
        "trials": [
            {
                "id": t.path.name,
                "agent": agent,
                "status": t.status,
                "failed_checks": _failed_checks(t, expected),
            }
            for agent, t in trials
        ],
    }


def _failed_checks(trial: TrialSummary, expected: dict) -> list[dict]:
    record = trial.record or {}
    checks = record.get("checks") or []
    snapshot_file = trial.path / "verifier/snapshot.json"
    snapshot = json.loads(snapshot_file.read_text()) if snapshot_file.exists() else {}
    found = diagnostics.diagnose(trial.path, expected, snapshot, checks)
    seen = {item["check"]: item for item in found["expected_value_seen"] or []}
    labelled = labels.label(trial.path, checks, call=False)["labels"]
    failures = []
    for check in checks:
        if check["passed"]:
            continue
        name = check["name"]
        value = None
        if name in expected:
            try:
                value = {
                    "value": expected[name](snapshot),
                    "seen": (seen.get(name) or {}).get("seen"),
                }
            except (KeyError, TypeError):
                # An error snapshot, or a fact the snapshot could not record.
                value = {"value": None, "seen": None}
        answers = labelled.get(name)
        failures.append(
            {
                "check": name,
                "required": check["required"],
                "notes": str(check.get("notes") or "")[:NOTES_CHARS],
                "expected": value,
                "labels": {question: answers[question] for question in labels.QUESTIONS}
                if answers
                else None,
                "error_stage": record.get("error_stage"),
            }
        )
    return failures


def _failures(given: dict) -> dict[tuple[str, str], dict]:
    return {
        (trial["id"], failure["check"]): failure
        for arm in given["arms"].values()
        for trial in arm["trials"]
        for failure in trial["failed_checks"]
    }


def _readme(path: Path) -> str:
    """The Treatment README's first paragraph after its title."""
    if not path.exists():
        return ""
    paragraphs = [
        p for p in path.read_text().split("\n\n") if p.strip() and not p.startswith("#")
    ]
    return " ".join(paragraphs[0].split()) if paragraphs else ""


def _prompt_diff(comparison: Comparison) -> str | None:
    """The unified diff from the baseline's prompt to the Treatment's, or
    ``None`` when the Treatment kept the Task's prompt."""
    prompts = comparison.prompts()
    if prompts is None:
        return None
    before, after = (prompt.splitlines() for prompt in prompts)
    # Without the "---"/"+++" file headers, which name no files here.
    return "\n".join(list(difflib.unified_diff(before, after, lineterm=""))[2:])


def _name(comparison: Comparison) -> str:
    """A file name unique to the comparison's grouping in ``compare_treatments``."""
    versions = "-".join(
        v or "unversioned"
        for v in (
            comparison.treatment_version,
            comparison.task_version,
            comparison.check_version,
        )
    )
    task = comparison.task.removeprefix("tasks/").replace("/", "__")
    return f"{comparison.treatment}__{task}__{versions}"
