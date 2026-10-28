"""Typed labels for a Trial's failed checks, in two stages.

First a long-context model (``STEPS_MODEL`` on OpenRouter) reads the whole
trace once per Trial and picks, for each failed check, the step where the
agent made the choice the check found (``decision_step``) and the other
steps that bear on it, each with a kind: ``source``, ``intent``,
``trigger``, or ``verification``. No relevant steps is a valid answer.

Then TypeSafe's Jev model reads only those steps, never the step finder's
reasons, and answers two Choice questions per failed check: ``cause`` (why
the agent made the choice, one of ``CAUSES``) and ``answer_source`` (which
source shown in those steps the value came from, or the agent's own
knowledge). Each answer carries Jev's confidence. Labels explain a failure;
they never change the score.

Answers are saved in ``<run>/labels/<trial>.json``, keyed by a hash of each
request, so a repeat costs nothing and any change to the prompts, the
options, the failed checks, or the Trial text asks again. Calls need
``OPENROUTER_API_KEY`` and ``TYPESAFEAI_API_KEY``.
"""

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from weval.diagnostics import URL

API = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
KEY_VAR = "TYPESAFEAI_API_KEY"
STEPS_API = "https://openrouter.ai/api/v1/chat/completions"
# Cheap, with a 1M-token context and strict structured outputs: a whole
# trace fits in one request.
STEPS_MODEL = "openai/gpt-6-luna"
STEPS_KEY_VAR = "OPENROUTER_API_KEY"
# Each message, reasoning, tool argument, and tool result is clipped to this
# many characters, keeping its head and tail, before the step finder reads it.
ITEM_CHARS = 8000
# The selected steps share one budget, split evenly, so each question stays
# inside Jev's default 32k-token per-question context (about 16k tokens
# here) without the long-context header.
STEPS_CHARS = 60_000
# Jev's Choice supports up to 255 options; one is the agent's own knowledge.
MAX_SOURCES = 254
# A call that returned less showed the agent nothing to take a value from,
# such as the write that saves an answer citing URLs.
MIN_SHOWN_CHARS = 200
# Pi's fetch_content and web_search results end with a responseId; the
# pages themselves arrive through get_search_content(responseId, urlIndex),
# whose arguments name no URL.
RESPONSE_ID = re.compile(r'responseId:?\s*"(\w+)"')
# Claude Code's Skill tool returns only "Launching skill"; the skill's text
# arrives as the next user message, which starts with its directory.
SKILL_BASE = re.compile(r"Base directory for this skill: \S*/skills/([^/\s]+)")
# The two Choice questions asked per failed check, in presentation order.
QUESTIONS = ("cause", "answer_source")
OWN_KNOWLEDGE = (
    "The agent's own knowledge: no source it was shown states the value or approach."
)
CAUSES = {
    "no_lookup": "It chose without looking anything up: no step before the decision shows it a source for the choice.",
    "followed_source": "It took the choice from something it was shown, such as a docs page, a search result, a skill file, or example code.",
    "ignored_current_practice": "It was shown the current practice the check looks for and chose otherwise without saying why.",
    "considered_and_rejected": "It weighed the option the check looks for and chose otherwise, giving a reason.",
    "environment_forced": "An observation, such as an error, a missing module, or a failed health check, pushed it to the choice.",
    "no_trace_evidence": "The steps shown do not explain the choice.",
}
STEPS_SYSTEM = """\
You read a coding agent's trace and find the steps that explain why it failed a check.

For each failed check, return:
- decision_step: the step where the agent made the choice that the check found, in its reasoning, its \
message, or a tool call. For something the agent left out, the step that wrote the code or file without it. \
Use the choice that survived to the end: if the agent changed its mind, the step of the final choice.
- relevant: every other step that bears on the decision, each with a kind:
  - source: a tool result that showed the agent something it could have taken the value or approach from, \
or that showed current practice it did not follow;
  - intent: the agent's reasoning or message about the choice;
  - trigger: an observation that made the agent change its choice;
  - verification: a later step where the agent checked, tested, or was warned about the choice.
  Give a short reason for each, naming what the step shows.
Return only steps that exist in the trace. If nothing in the trace bears on the choice, return a null \
decision_step and an empty list: that is a valid answer."""
KINDS = ("source", "intent", "trigger", "verification")


def label(trial_dir: Path, results: list[dict], *, call: bool = True) -> dict:
    """Labels for each failed check in ``results`` (``verify.score`` rows).

    Returns ``{"labels": {check: answers}, "note": str | None}``. Each
    check's answers are ``{"model", "steps_model", "decision_step",
    "steps", "cause", "answer_source"}``: ``steps`` lists the relevant
    steps as ``{"step", "kind", "why"}`` by trajectory ``step_id``, and
    ``cause`` and ``answer_source`` are ``{"choice", "confidence"}``.
    ``answer_source``'s choice is a URL, a Treatment file path, a search,
    or ``own-knowledge``. With ``call`` false, or without either API key,
    only saved answers are returned and ``note`` says what was skipped. A
    failed request is skipped with a ``note`` rather than raised, so
    labelling never stops a run. A Trial whose snapshot failed is not
    labelled: its checks failed without observing a value to trace.
    """
    failed = [r for r in results if not r["passed"]]
    trajectory = trial_dir / "agent/trajectory.json"
    if not failed or not trajectory.exists():
        return {"labels": {}, "note": None}
    snapshot = trial_dir / "verifier/snapshot.json"
    if snapshot.exists() and "error" in json.loads(snapshot.read_text()):
        return {"labels": {}, "note": "unlabelled: the snapshot failed"}
    steps = _numbered(json.loads(trajectory.read_text())["steps"])
    names = _source_names(steps, trial_dir.parents[1] / "treatment/skills")

    cache_file = trial_dir.parents[1] / "labels" / f"{trial_dir.name}.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    before = json.dumps(cache)
    checks_cache = cache.setdefault("checks", {})
    missing = [var for var in (STEPS_KEY_VAR, KEY_VAR) if not os.environ.get(var)]
    can_call = call and not missing

    labels, skipped, failure = {}, [], None
    try:
        found = _cached(
            cache,
            "steps",
            _steps_request(steps, failed),
            lambda body: (
                _ask_steps(body, os.environ[STEPS_KEY_VAR]) if can_call else None
            ),
        )
    except httpx.HTTPError as error:
        found, failure = None, f"step selection failed: {error}"
    selections = {row["check"]: row for row in (found or {}).get("checks", [])}
    for result in failed:
        name = result["name"]
        if found is None:
            skipped.append(name)
            continue
        selection = _valid(selections.get(name), steps)
        sources = _selected_sources(selection, names)
        try:
            response = _cached(
                checks_cache,
                name,
                _request(result, selection, steps, sources),
                lambda body: _post(body, os.environ[KEY_VAR]) if can_call else None,
            )
        except httpx.HTTPError as error:
            skipped.append(f"{name} ({error})")
            continue
        if response is None:
            skipped.append(name)
            continue
        labels[name] = _decode(response, list(sources), selection, found["model"])

    if json.dumps(cache) != before:
        cache_file.parent.mkdir(exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=1))
    note = None
    if skipped:
        reason = (
            failure
            or ("not requested" if not call else None)
            or (f"{' and '.join(missing)} not set" if missing else "request failed")
        )
        note = f"unlabelled ({reason}): {', '.join(skipped)}"
    return {"labels": labels, "note": note}


def _cached(
    entries: dict, name: str, body: dict, post: Callable[[dict], dict | None]
) -> dict | None:
    """The response saved under ``name`` for this exact ``body``, else
    ``post(body)``'s, saved in ``entries``; ``None`` when neither exists."""
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    saved = entries.get(name)
    if saved and saved["request_sha256"] == digest:
        return saved["response"]
    response = post(body)
    if response is not None:
        entries[name] = {"request_sha256": digest, "response": response}
    return response


def _numbered(steps: list[dict]) -> dict[int, dict]:
    """Steps by Harbor's ``step_id``, the number the report's transcript
    shows; positions from 1 where a trajectory has none."""
    return {step.get("step_id", i + 1): step for i, step in enumerate(steps)}


def _source_names(steps: dict[int, dict], skills: Path) -> dict[int, list[str]]:
    """What each step showed the agent, by name: each fetched URL, search,
    and Treatment file whose tool call returned at least
    ``MIN_SHOWN_CHARS``. A page Pi read with ``get_search_content`` counts
    for the URL or search that stored it, and a skill Claude Code loaded
    counts for its ``SKILL.md`` in the step that shows its text."""
    treatment_files = (
        [str(p.relative_to(skills)) for p in skills.rglob("*") if p.is_file()]
        if skills.is_dir()
        else []
    )
    shown: dict[int, list[str]] = {}
    # responseId -> the URLs the storing call fetched, and the names it got.
    responses: dict[str, tuple[list, list[str]]] = {}
    for number, step in steps.items():
        names = shown.setdefault(number, [])
        skill = SKILL_BASE.match(str(step.get("message") or ""))
        if (
            step.get("source") == "user"
            and skill
            and f"{skill[1]}/SKILL.md" in treatment_files
        ):
            names.append(f"{skill[1]}/SKILL.md")
        results = {
            r.get("source_call_id"): str(r.get("content") or "")
            for r in (step.get("observation") or {}).get("results", [])
        }
        for call in step.get("tool_calls") or []:
            content = results.get(call.get("tool_call_id"), "")
            if len(content) < MIN_SHOWN_CHARS:
                continue
            arguments = json.dumps(call.get("arguments"))
            found = URL.findall(arguments)
            # Web search tools (Claude Code's WebSearch, Pi's web_search), not ToolSearch.
            if (
                call["function_name"].lower().replace("_", "") == "websearch"
                and not found
            ):
                found = [
                    f"search: {(call.get('arguments') or {}).get('query', arguments)}"
                ]
            found += [f for f in treatment_files if Path(f).name in arguments]
            given = call.get("arguments") or {}
            stored = RESPONSE_ID.search(content)
            if stored and ("urls" in given or "queries" in given):
                responses[stored[1]] = (given.get("urls") or [], found)
                # Only page titles: the pages count when they are read.
                if content.startswith("## Fetched URLs"):
                    continue
            if call["function_name"] == "get_search_content":
                urls, origin = responses.get(given.get("responseId"), ([], []))
                index = given.get("urlIndex")
                in_range = isinstance(index, int) and 0 <= index < len(urls)
                found = [urls[index]] if in_range else origin
            names += [name for name in found if name not in names]
    return {number: names for number, names in shown.items() if names}


def _steps_request(steps: dict[int, dict], failed: list[dict]) -> dict:
    checks = "\n".join(
        f"- {r['name']} ({'required' if r.get('required', True) else 'preferred'}): "
        f"{r.get('description') or ''} Failure: {r.get('notes') or ''}"
        for r in failed
    )
    trace = "\n".join(_render(number, step) for number, step in steps.items())
    # The check names are an enum, so each answer names a check exactly.
    relevant = {
        "type": "object",
        "additionalProperties": False,
        "required": ["step", "kind", "why"],
        "properties": {
            "step": {"type": "integer"},
            "kind": {"type": "string", "enum": list(KINDS)},
            "why": {"type": "string"},
        },
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["checks"],
        "properties": {
            "checks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["check", "decision_step", "relevant"],
                    "properties": {
                        "check": {
                            "type": "string",
                            "enum": [r["name"] for r in failed],
                        },
                        "decision_step": {"type": ["integer", "null"]},
                        "relevant": {"type": "array", "items": relevant},
                    },
                },
            }
        },
    }
    return {
        "model": STEPS_MODEL,
        "messages": [
            {"role": "system", "content": STEPS_SYSTEM},
            {
                "role": "user",
                "content": f"Failed checks:\n{checks}\n\nTrace ({len(steps)} steps):\n{trace}",
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "steps", "strict": True, "schema": schema},
        },
    }


def _render(number: int, step: dict) -> str:
    """One step as text: reasoning, message, and each tool call with its
    result, each item clipped to ``ITEM_CHARS``."""
    results = {
        r.get("source_call_id"): r.get("content")
        for r in (step.get("observation") or {}).get("results", [])
    }
    lines = [f"### Step {number} ({step.get('source')})"]
    for key in ("reasoning_content", "message"):
        if step.get(key):
            lines.append(f"{key}: {_clip(str(step[key]), ITEM_CHARS)}")
    for call in step.get("tool_calls") or []:
        arguments = json.dumps(call.get("arguments"))
        result = str(results.get(call.get("tool_call_id")) or "")
        lines.append(
            f"tool call {call['function_name']}: {_clip(arguments, ITEM_CHARS)}"
        )
        lines.append(f"result: {_clip(result, ITEM_CHARS)}")
    return "\n".join(lines)


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n[... {len(text) - limit} chars cut ...]\n{text[-half:]}"


def _valid(selection: dict | None, steps: dict[int, dict]) -> dict:
    """The step finder's answer for one check without steps the trace lacks;
    a check it did not answer has no relevant steps."""
    selection = selection or {"decision_step": None, "relevant": []}
    decision = selection["decision_step"]
    return {
        "decision_step": decision if decision in steps else None,
        "relevant": [r for r in selection["relevant"] if r["step"] in steps],
    }


def _selected_sources(
    selection: dict, names: dict[int, list[str]]
) -> dict[str, list[int]]:
    """Each source the selected steps showed, with the steps that showed it,
    in step order; at most ``MAX_SOURCES``."""
    sources: dict[str, list[int]] = {}
    for number in _selected_steps(selection):
        for name in names.get(number, []):
            sources.setdefault(name, []).append(number)
    return dict(list(sources.items())[:MAX_SOURCES])


def _selected_steps(selection: dict) -> list[int]:
    numbers = {r["step"] for r in selection["relevant"]}
    if selection["decision_step"] is not None:
        numbers.add(selection["decision_step"])
    return sorted(numbers)


def _request(
    result: dict,
    selection: dict,
    steps: dict[int, dict],
    sources: dict[str, list[int]],
) -> dict:
    # Jev sees the steps' own text with their kinds, not the step finder's
    # reasons, so a wrong reason cannot steer the label.
    kinds = {r["step"]: r["kind"] for r in selection["relevant"]}
    if selection["decision_step"] is not None:
        kinds[selection["decision_step"]] = "decision"
    numbers = _selected_steps(selection)
    share = STEPS_CHARS // max(len(numbers), 1)
    shown = [_clip(f"[{kinds[n]}]\n{_render(n, steps[n])}", share) for n in numbers]
    # Option ids are positional; names go in the descriptions, which Jev
    # reads, and _decode maps the ids back.
    options = {
        f"source_{i:03d}": f"{name} (shown in step {', '.join(map(str, shown_in))})"
        for i, (name, shown_in) in enumerate(sources.items())
    }
    options["own_knowledge"] = OWN_KNOWLEDGE
    return {
        "model": MODEL,
        "state": {
            "failed_check": f"{result['name']}: {result.get('notes') or ''}",
            "steps": shown,
        },
        "questions": {
            "cause": {
                "type": "choice",
                "instructions": "Why did the agent make the choice the failed check found?",
                "criteria": CAUSES,
            },
            "answer_source": {
                "type": "choice",
                "instructions": "Which source did the agent take the value or approach in the failed check from?",
                "criteria": options,
            },
        },
    }


def _ask_steps(body: dict, key: str) -> dict:
    """The step finder's parsed answer, with the model that gave it."""
    for attempt in range(3):
        response = httpx.post(
            STEPS_API,
            json=body,
            headers={"Authorization": f"Bearer {key}"},
            timeout=600,
        )
        if response.status_code in (429, 502, 503) and attempt < 2:
            time.sleep(5 * (attempt + 1))
            continue
        response.raise_for_status()
        data = response.json()
        return {
            "model": data.get("model"),
            "checks": json.loads(data["choices"][0]["message"]["content"])["checks"],
            "usage": data.get("usage"),
        }
    raise AssertionError("unreachable")


def _post(body: dict, key: str) -> dict:
    for attempt in range(3):
        response = httpx.post(
            API, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=60
        )
        # 429 rate limit and 529 overloaded: back off and retry, as TypeSafe's docs ask.
        if response.status_code in (429, 529) and attempt < 2:
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        return response.json()
    raise AssertionError("unreachable")


def _decode(
    response: dict, sources: list[str], selection: dict, steps_model: str | None
) -> dict:
    names = dict(zip((f"source_{i:03d}" for i in range(len(sources))), sources))
    names["own_knowledge"] = "own-knowledge"
    answers = response["answers"]
    cause, source = answers["cause"], answers["answer_source"]
    return {
        "model": response.get("model"),
        "steps_model": steps_model,
        "decision_step": selection["decision_step"],
        "steps": selection["relevant"],
        "cause": {"choice": cause["choice"], "confidence": cause.get("confidence")},
        "answer_source": {
            "choice": names.get(source["choice"], source["choice"]),
            "confidence": source.get("confidence"),
        },
    }
