"""Typed labels for a Trial's failed checks, from TypeSafe's Jev model.

For each failed check, Jev answers two Choice questions over what the Trial
saw: ``answer_source`` (which of the Trial's sources, or the agent's own
knowledge, the failed value came from) and ``verification`` (what the agent
did about that value). Each answer carries Jev's confidence and per-option
probabilities. Labels explain a failure; they never change the score.

Answers are saved in ``<run>/labels/<trial>.json``, keyed by a hash of the
request, so a repeat costs nothing and any change to the question wording,
the options, or the Trial text asks again. Calls need ``TYPESAFEAI_API_KEY``.
"""

import hashlib
import json
import os
import time
from pathlib import Path

import httpx

from weval.diagnostics import URL

API = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
KEY_VAR = "TYPESAFEAI_API_KEY"
# Per source and per agent message, so a request stays a few thousand tokens.
EXCERPT_CHARS = 3000
MESSAGE_CHARS = 600
# Jev's Choice supports up to 255 options; one is the agent's own knowledge.
MAX_SOURCES = 254
# A call that returned less showed the agent nothing to take a value from,
# such as the write that saves an answer citing URLs.
MIN_SHOWN_CHARS = 200
OWN_KNOWLEDGE = "The agent's own knowledge: no source it was shown states the value or approach."
VERIFICATION = {
    "verified": "It checked the value against a source that states it before answering.",
    "deferred_to_user": "It said the value was unconfirmed and told the user how to confirm it.",
    "not_attempted": "It said the value was unconfirmed, or did not look, without telling the user how to confirm it.",
    "guessed": "It stated the value as fact without checking it or saying it was unconfirmed.",
}


def label(trial_dir: Path, results: list[dict], *, call: bool = True) -> dict:
    """Labels for each failed check in ``results`` (``verify.score`` rows).

    Returns ``{"labels": {check: {"model", "answer_source", "verification"}},
    "note": str | None}``. Each answer is ``{"choice", "confidence"}``;
    ``answer_source``'s choice is a URL, a Treatment file path, a search, or
    ``own-knowledge``. With ``call`` false, or without the API key, only
    saved answers are returned and ``note`` says what was skipped. A failed
    request is skipped with a ``note`` rather than raised, so labelling never
    stops a run.
    """
    failed = [r for r in results if not r["passed"]]
    trajectory = trial_dir / "agent/trajectory.json"
    if not failed or not trajectory.exists():
        return {"labels": {}, "note": None}
    steps = json.loads(trajectory.read_text())["steps"]
    sources = _sources(steps, trial_dir.parents[1] / "treatment/skills")
    messages = [str(s["message"])[:MESSAGE_CHARS] for s in steps if s.get("source") == "agent" and s.get("message")]

    cache_file = trial_dir.parents[1] / "labels" / f"{trial_dir.name}.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    key = os.environ.get(KEY_VAR)
    labels, skipped, changed = {}, [], False
    for result in failed:
        body = _request(result, sources, messages)
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        saved = cache.get(result["name"])
        if saved and saved["request_sha256"] == digest:
            labels[result["name"]] = _decode(saved["response"], sources)
            continue
        if not (call and key):
            skipped.append(result["name"])
            continue
        try:
            response = _post(body, key)
        except httpx.HTTPError as error:
            skipped.append(f"{result['name']} ({error})")
            continue
        cache[result["name"]] = {"request_sha256": digest, "response": response}
        labels[result["name"]] = _decode(response, sources)
        changed = True

    if changed:
        cache_file.parent.mkdir(exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=1))
    note = None
    if skipped:
        reason = "not requested" if not call else f"{KEY_VAR} is not set" if not key else "request failed"
        note = f"unlabelled ({reason}): {', '.join(skipped)}"
    return {"labels": labels, "note": note}


def _sources(steps: list[dict], skills: Path) -> dict[str, str]:
    """What the Trial looked up, by name, with an excerpt of what it was shown:
    each fetched URL, search, and named Treatment file whose tool call
    returned at least ``MIN_SHOWN_CHARS``, in first-use order."""
    shown = {r.get("source_call_id"): str(r.get("content") or "")
             for s in steps for r in (s.get("observation") or {}).get("results", [])}
    treatment_files = [str(p.relative_to(skills)) for p in skills.rglob("*") if p.is_file()] if skills.is_dir() else []
    sources: dict[str, str] = {}
    for step in steps:
        for call in step.get("tool_calls") or []:
            if len(shown.get(call.get("tool_call_id"), "")) < MIN_SHOWN_CHARS:
                continue
            arguments = json.dumps(call.get("arguments"))
            names = URL.findall(arguments)
            # Web search tools (Claude Code's WebSearch, Pi's web_search), not ToolSearch.
            if call["function_name"].lower().replace("_", "") == "websearch" and not names:
                names = [f"search: {(call.get('arguments') or {}).get('query', arguments)}"]
            names += [f for f in treatment_files if Path(f).name in arguments]
            for name in names:
                excerpt = sources.get(name, "") + shown.get(call.get("tool_call_id"), "")
                sources[name] = excerpt[:EXCERPT_CHARS]
    return dict(list(sources.items())[:MAX_SOURCES])


def _request(result: dict, sources: dict[str, str], messages: list[str]) -> dict:
    # Option ids are positional; names and excerpts go in the descriptions,
    # which Jev reads, and _decode maps the ids back.
    options = {f"source_{i:03d}": f"{name}\n{excerpt}" for i, (name, excerpt) in enumerate(sources.items())}
    options["own_knowledge"] = OWN_KNOWLEDGE
    return {
        "model": MODEL,
        "state": {"failed_check": f"{result['name']}: {result['notes']}", "agent_messages": messages},
        "questions": {
            "answer_source": {
                "type": "choice",
                "instructions": "Which source did the agent take the value or approach in the failed check from?",
                "criteria": options,
            },
            "verification": {
                "type": "choice",
                "instructions": "What did the agent do about the value or approach the failed check looks for?",
                "criteria": VERIFICATION,
            },
        },
    }


def _post(body: dict, key: str) -> dict:
    for attempt in range(3):
        response = httpx.post(API, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=60)
        # 429 rate limit and 529 overloaded: back off and retry, as TypeSafe's docs ask.
        if response.status_code in (429, 529) and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        response.raise_for_status()
        return response.json()
    raise AssertionError("unreachable")


def _decode(response: dict, sources: dict[str, str]) -> dict:
    names = dict(zip((f"source_{i:03d}" for i in range(len(sources))), sources))
    names["own_knowledge"] = "own-knowledge"
    answers = response["answers"]
    source, verification = answers["answer_source"], answers["verification"]
    return {
        "model": response.get("model"),
        "answer_source": {"choice": names.get(source["choice"], source["choice"]), "confidence": source.get("confidence")},
        "verification": {"choice": verification["choice"], "confidence": verification.get("confidence")},
    }
