"""The analyst reads computed facts about one Treatment comparison; its answer
is checked against those facts, saved beside the runs, and asked again only
when the request changes. No test calls the network: ``analysis._post`` is
replaced with a fake analyst."""

import json
from pathlib import Path

import pytest

from weval import analysis
from weval.collect import collect_runs, compare_treatments

BASELINE = "20261027-154757__investigate__current-practices__claude-code-sonnet-5.5"
TREATED = BASELINE.replace("154757", "154759") + "+weaviate-docs"
EXPECTED = {
    "python-client-version-latest": lambda snapshot: snapshot["python_client_version"]
}
VERSION, VECTOR = "python-client-version-latest", "current-vector-config"


def write_trial(
    run_dir: Path,
    name: str,
    failed: list[str],
    shown: str = "",
    treatment: str | None = None,
) -> None:
    trial = run_dir / "job" / name
    (trial / "agent").mkdir(parents=True)
    (trial / "verifier").mkdir()
    checks = [
        {
            "name": check,
            "required": True,
            "passed": check not in failed,
            "notes": f"{check} failed",
        }
        for check in (VERSION, VECTOR)
    ]
    (trial / "weval.json").write_text(
        json.dumps(
            {
                "status": "failed" if failed else "passed",
                "task": "tasks/investigate/current-practices",
                "treatment": treatment,
                "agent": {"name": "claude-code-sonnet-5.5"},
                "checks": checks,
                "usage": {
                    "n_input_tokens": 1000,
                    "n_cache_tokens": 400,
                    "cost_usd": 0.1,
                },
            }
        )
    )
    (trial / "verifier/snapshot.json").write_text(
        json.dumps({"python_client_version": "4.24.1"})
    )
    steps = [
        {"source": "user", "message": "Answer."},
        {
            "source": "agent",
            "message": "Reading.",
            "observation": {"results": [{"content": shown}]},
        },
    ]
    (trial / "agent/trajectory.json").write_text(json.dumps({"steps": steps}))


@pytest.fixture
def comparison(tmp_path):
    write_trial(
        tmp_path / BASELINE,
        "task__base1",
        [VERSION],
        shown="The latest Python client is 4.24.1.",
    )
    write_trial(tmp_path / BASELINE, "task__base2", [VECTOR])
    write_trial(tmp_path / TREATED, "task__treat1", [], treatment="weaviate-docs")
    write_trial(
        tmp_path / TREATED,
        "task__treat2",
        [VERSION],
        shown="Python 4.24.x",
        treatment="weaviate-docs",
    )
    (tmp_path / TREATED / "treatment").mkdir()
    (tmp_path / TREATED / "treatment/README.md").write_text(
        "# weaviate-docs\n\nQuestion: does a local copy\nhelp?\n"
    )
    [found] = compare_treatments(collect_runs(tmp_path))
    return found


def answer(**changes) -> dict:
    """An answer that passes ``verify`` against the ``comparison`` fixture."""
    patterns = [
        {
            "summary": "Client patch missed",
            "checks": [VERSION],
            "trials": ["task__base1", "task__treat2"],
            "evidence": "expected 4.24.1",
            "class": "Weaviate gap",
            "reason": "the docs give the minor line",
        },
        {
            "summary": "Vector API unnamed",
            "checks": [VECTOR],
            "trials": ["task__base2"],
            "evidence": "failed",
            "class": "agent gap",
            "reason": "the answer names no API",
        },
    ]
    return {
        "result": "The Treatment passed 1 of 2 against 0 of 2, helping 1 agent.",
        "patterns": patterns,
        "caveats": ["2 Trials per arm."],
        "open_questions": [],
        **changes,
    }


class FakeAnalyst:
    """Gives each prepared answer in turn, and records each request."""

    def __init__(self, *answers: dict):
        self.answers, self.requests = list(answers), []

    def __call__(self, body: dict, key: str) -> dict:
        self.requests.append(body)
        text = json.dumps(self.answers[min(len(self.requests), len(self.answers)) - 1])
        return {
            "model": "anthropic/claude-sonnet-5.5",
            "stop_reason": "end_turn",
            "content": [
                {"type": "thinking", "thinking": "", "signature": "s"},
                {"type": "text", "text": text},
            ],
        }


def use(monkeypatch, fake: FakeAnalyst) -> FakeAnalyst:
    monkeypatch.setattr(analysis, "_post", fake)
    monkeypatch.setenv(analysis.KEY_VAR, "test-key")
    return fake


def test_facts_give_each_arm_its_statistics_and_each_failure_its_evidence(comparison):
    given = analysis.facts(comparison, EXPECTED)

    base, treated = given["arms"]["baseline"], given["arms"]["treatment"]
    assert (base["passed"], base["scored"], treated["passed"], treated["scored"]) == (
        0,
        2,
        1,
        2,
    )
    assert given["agents"] == [
        {
            "agent": "claude-code-sonnet-5.5",
            "baseline": {"scored": 2, "passed": 0},
            "treatment": {"scored": 2, "passed": 1},
            "change": "helped",
        }
    ]
    assert given["agent_changes"] == {"helped": 1}
    assert {t["agent"] for t in treated["trials"]} == {"claude-code-sonnet-5.5"}
    assert base["mean_uncached_input_tokens"] == 600
    # Both arms record identical usage, so every change is zero percent.
    assert given["median_usage_change_percent"] == {
        "cost_usd": 0,
        "uncached_input": 0,
        "turns": 0,
    }
    assert given["treatment_readme"] == "Question: does a local copy help?"
    failures = {
        (t["id"], f["check"]): f
        for arm in (base, treated)
        for t in arm["trials"]
        for f in t["failed_checks"]
    }
    assert failures["task__base1", VERSION]["expected"] == {
        "value": "4.24.1",
        "seen": True,
    }
    assert failures["task__treat2", VERSION]["expected"] == {
        "value": "4.24.1",
        "seen": False,
    }
    assert failures["task__base2", VECTOR]["expected"] is None


RELEASE_NOTES = {
    "choice": "https://docs.weaviate.io/weaviate/release-notes",
    "confidence": 0.92,
}


@pytest.mark.parametrize(
    ("expected", "source", "proposed"),
    [
        ({"value": "4.24.1", "seen": False}, RELEASE_NOTES, "Weaviate gap"),
        ({"value": "4.24.1", "seen": True}, RELEASE_NOTES, "agent gap"),
        ({"value": None, "seen": None}, None, "infrastructure failure"),
        (
            {"value": "4.24.1", "seen": False},
            {"choice": "own-knowledge", "confidence": 0.9},
            "unclassified",
        ),
        # A Treatment file copied from the docs is weval's content, not a Weaviate page.
        (
            {"value": "4.24.1", "seen": False},
            {"choice": "weaviate-docs/pages/release-notes.md", "confidence": 0.5},
            "unclassified",
        ),
        (None, RELEASE_NOTES, "unclassified"),
    ],
)
def test_the_rule_proposes_a_class_only_where_its_evidence_decides_one(
    expected, source, proposed
):
    failure = {
        "check": VERSION,
        "required": True,
        "notes": "",
        "expected": expected,
        "labels": {"answer_source": source} if source else None,
    }

    assert analysis.propose_class(failure)["class"] == proposed


def test_an_accepted_analysis_is_saved_reused_and_cross_checked(
    tmp_path, comparison, monkeypatch
):
    fake = use(monkeypatch, FakeAnalyst(answer()))

    result = analysis.analyse(comparison, EXPECTED, tmp_path)

    assert (
        result["analysis"] == answer()
        and result["problems"] == []
        and result["note"] is None
    )
    # task__base1 was shown 4.24.1, so the rule calls its failure an agent gap.
    assert result["disagreements"] == [
        {
            "trial": "task__base1",
            "check": VERSION,
            "class": "agent gap",
            "reason": "the agent was shown 4.24.1 and answered otherwise",
            "analyst": "Weaviate gap",
        }
    ]
    assert len(list((tmp_path / analysis.DIRECTORY).glob("*.json"))) == 1
    assert analysis.analyse(comparison, EXPECTED, tmp_path)["analysis"] == answer()
    assert (
        analysis.analyse(comparison, EXPECTED, tmp_path, call=False)["analysis"]
        == answer()
    )
    assert len(fake.requests) == 1


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"result": "The Treatment passed 7 of 2."}, "numbers not in the facts: 7 ("),
        (
            {
                "patterns": [
                    {
                        **answer()["patterns"][0],
                        "trials": ["task__base1", "task__treat2", "task__treat1"],
                    },
                    answer()["patterns"][1],
                ]
            },
            "Trial 'task__treat1' did not fail any of the pattern's checks",
        ),
        (
            {"patterns": answer()["patterns"][:1]},
            f"failed required check '{VECTOR}' of Trial 'task__base2' is in no pattern",
        ),
        (
            {"patterns": [{**answer()["patterns"][0], "checks": ["hybrid-query"]}]},
            "'hybrid-query' is not a failed check",
        ),
    ],
)
def test_verify_names_what_the_facts_do_not_support(comparison, change, problem):
    problems = analysis.verify(answer(**change), analysis.facts(comparison, EXPECTED))

    assert any(problem in p for p in problems), problems


def test_a_rejected_answer_is_asked_again_with_its_problems(
    tmp_path, comparison, monkeypatch
):
    wrong = answer(result="The Treatment passed 7 of 2.")
    fake = use(monkeypatch, FakeAnalyst(wrong, answer()))

    assert analysis.analyse(comparison, EXPECTED, tmp_path)["analysis"] == answer()

    retry = fake.requests[1]["messages"]
    assert [m["role"] for m in retry] == ["user", "assistant", "user"]
    assert retry[1]["content"][0]["type"] == "thinking"
    assert "numbers not in the facts: 7 (" in retry[2]["content"]


def test_an_answer_rejected_every_time_is_saved_as_rejected(
    tmp_path, comparison, monkeypatch
):
    fake = use(monkeypatch, FakeAnalyst(answer(result="The Treatment passed 7 of 2.")))

    result = analysis.analyse(comparison, EXPECTED, tmp_path)

    assert (
        result["analysis"] is None
        and "numbers not in the facts: 7 (" in result["problems"][0]
    )
    assert len(fake.requests) == analysis.ATTEMPTS
    # Saved, so the rejection is not paid for again, and the rule still answers.
    assert (
        analysis.analyse(comparison, EXPECTED, tmp_path)["problems"]
        == result["problems"]
    )
    assert len(fake.requests) == analysis.ATTEMPTS
    assert {r["class"] for r in result["rule"]} == {"agent gap", "unclassified"}


def test_without_the_key_or_a_call_no_request_is_made(
    tmp_path, comparison, monkeypatch
):
    fake = use(monkeypatch, FakeAnalyst(answer()))

    assert (
        analysis.analyse(comparison, EXPECTED, tmp_path, call=False)["note"]
        == "not analysed (not requested)"
    )
    monkeypatch.delenv(analysis.KEY_VAR)
    assert analysis.analyse(comparison, EXPECTED, tmp_path)["note"] == (
        f"not analysed ({analysis.KEY_VAR} is not set)"
    )
    assert fake.requests == []


def test_the_analyst_sees_a_treatments_prompt_change_as_a_line_diff():
    class Replaced:
        def prompts(self):
            return (
                "Fix the SKU search.\nShared notes.\n",
                "Use docs.example.\nShared notes.\n",
            )

    class Kept:
        def prompts(self):
            return None

    assert analysis._prompt_diff(Replaced()) == (
        "@@ -1,2 +1,2 @@\n-Fix the SKU search.\n+Use docs.example.\n Shared notes."
    )
    assert analysis._prompt_diff(Kept()) is None
