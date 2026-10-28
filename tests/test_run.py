"""Recording and re-scoring Trials: ``finalize`` writes ``weval.json``
(status, usage, Treatment, fingerprints), ``derive_status`` grades outcomes,
``package_task`` builds the Harbor package with its compose overlays, and
``weval check`` resolves the recorded repository-relative Task path from any
working directory."""

import json
import shutil
from pathlib import Path

import pytest

import weval.run
from weval.harnesses import claude_code, pi
from weval.rescore import check_versions, rescore
from weval.run import (
    ROOT,
    SHARED_COMPOSE,
    SHARED_INSTRUCTIONS,
    WEAVIATE_COMPOSE,
    check_fingerprint,
    compose_overlays,
    derive_status,
    finalize,
    finalize_run,
    fingerprints,
    package_task,
    run,
    treatment_files,
)

TASK_PATH = Path("tasks/resolve/sku-search")
ORACLE_SNAPSHOT = ROOT / "tests/fixtures/resolve-sku-search-oracle-snapshot.json"


def test_finalize_records_task_path_and_rescore_resolves_it(tmp_path, monkeypatch):
    trial = tmp_path / "trial"
    (trial / "verifier").mkdir(parents=True)
    (trial / "result.json").write_text(
        json.dumps({"verifier_result": {"rewards": {"reward": 1}}})
    )
    shutil.copy(ORACLE_SNAPSHOT, trial / "verifier/snapshot.json")

    record = finalize(trial, TASK_PATH, {"name": "oracle", "harness": "oracle"})
    assert record["task"] == "tasks/resolve/sku-search"

    monkeypatch.chdir(tmp_path)
    results = rescore(trial)
    assert results and all(r["passed"] for r in results)


def test_check_versions_compares_the_current_check_with_the_recorded_one(tmp_path):
    trial = tmp_path / "trial"
    trial.mkdir()
    (trial / "result.json").write_text(
        json.dumps({"verifier_result": {"rewards": {"reward": 1}}})
    )
    oracle = {"name": "oracle", "harness": "oracle"}
    current = check_fingerprint(ROOT / TASK_PATH / "check.py")

    finalize(
        trial,
        TASK_PATH,
        oracle,
        versions={"task": "t", "check": current, "treatment": None},
    )
    assert check_versions(trial) == (current, current)

    finalize(trial, TASK_PATH, oracle)
    assert check_versions(trial) == (current, None)


def test_finalize_records_usage_from_result_and_trajectory(tmp_path):
    # Tool-call shapes copied from retained Pi Trials: a web search, a fetch,
    # and curl in bash, plus a probe of the Trial's own Weaviate.
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "result.json").write_text(
        json.dumps(
            {
                "agent_result": {
                    "n_input_tokens": 1080469,
                    "n_cache_tokens": 1023424,
                    "n_output_tokens": 33356,
                    "cost_usd": 0.028,
                }
            }
        )
    )
    calls = [
        (
            "web_search",
            {"queries": ["Weaviate latest stable version", "weaviate-client latest"]},
        ),
        ("fetch_content", {"url": "https://docs.weaviate.io/deploy/migration"}),
        (
            "bash",
            {
                "command": 'curl -s "https://api.github.com/repos/weaviate/weaviate/releases?per_page=15"'
            },
        ),
        (
            "bash",
            {
                "command": "curl -s http://weaviate:8080/v1/meta && curl http://127.0.0.1:8000/search"
            },
        ),
        ("fetch_content", {"url": "https://docs.weaviate.io/deploy/migration"}),
        # Claude Code loading its web tools: not a search.
        ("ToolSearch", {"query": "select:WebFetch,WebSearch", "max_results": 2}),
    ]
    (trial / "agent/trajectory.json").write_text(
        json.dumps(
            {
                "steps": [
                    {"tool_calls": [{"function_name": name, "arguments": arguments}]}
                    for name, arguments in calls
                ]
            }
        )
    )

    usage = finalize(trial, TASK_PATH, {"name": "oracle", "harness": "oracle"})["usage"]

    assert usage == {
        "n_input_tokens": 1080469,
        "n_cache_tokens": 1023424,
        "n_output_tokens": 33356,
        "cost_usd": 0.028,
        "tool_calls": {"web_search": 1, "fetch_content": 2, "bash": 2, "ToolSearch": 1},
        "urls": [
            "https://docs.weaviate.io/deploy/migration",
            "https://api.github.com/repos/weaviate/weaviate/releases?per_page=15",
        ],
        "search_queries": ["Weaviate latest stable version", "weaviate-client latest"],
    }


def test_finalize_takes_claude_code_tokens_from_its_model_usage(tmp_path):
    # Figures from Trial 20261016-105100 (claude-code-haiku-5.5): Harbor's
    # counts miss the requests in which WebFetch summarises each page.
    # OpenRouter billed $0.04 for it.
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "result.json").write_text(
        json.dumps(
            {
                "agent_result": {
                    "n_input_tokens": 437709,
                    "n_cache_tokens": 383347,
                    "n_output_tokens": 10094,
                    "cost_usd": 2.235776,
                }
            }
        )
    )
    final_event = {
        "type": "result",
        "modelUsage": {
            "anthropic/claude-haiku-5.5": {
                "inputTokens": 163888,
                "outputTokens": 35401,
                "cacheReadInputTokens": 383347,
                "cacheCreationInputTokens": 54342,
                "costUSD": 2.235776,
                "costBasis": "unknown",
            }
        },
    }
    (trial / "agent/claude-code.txt").write_text(
        f'{{"type": "system"}}\n{json.dumps(final_event)}\n'
    )

    agent = {"name": "claude-code-haiku-5.5", "harness": "claude-code"}
    usage = finalize(trial, TASK_PATH, agent)["usage"]

    assert {
        k: usage[k]
        for k in (
            "n_input_tokens",
            "n_cache_tokens",
            "n_cache_creation_tokens",
            "n_output_tokens",
            "cost_usd",
        )
    } == {
        "n_input_tokens": 601577,
        "n_cache_tokens": 383347,
        "n_cache_creation_tokens": 54342,
        "n_output_tokens": 35401,
        "cost_usd": pytest.approx(0.0447155),
    }


def test_claude_code_cost_covers_the_webfetch_model_and_rejects_unpriced_ones():
    # Figures from Trial 20261021-010554 (claude-code-sonnet-5.5): WebFetch's
    # summaries ran on Haiku 4.5, under a dated key.
    model_usage = {
        "claude-sonnet-5-5": {
            "inputTokens": 12,
            "outputTokens": 3375,
            "cacheReadInputTokens": 104873,
            "cacheCreationInputTokens": 11876,
            "canonicalModel": "claude-sonnet-5-5",
        },
        "claude-haiku-4-5-20251001": {
            "inputTokens": 135580,
            "outputTokens": 2573,
            "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0,
            "canonicalModel": "claude-haiku-4-5",
        },
    }
    assert claude_code.cost_usd(model_usage) == pytest.approx(0.2223963)
    assert (
        claude_code.cost_usd(model_usage | {"claude-unpriced": {"inputTokens": 1}})
        is None
    )


def test_package_task_uses_the_tasks_prompt_or_a_treatments(tmp_path):
    package_task(ROOT / TASK_PATH, tmp_path / "task")
    replacement = tmp_path / "prompt.md"
    replacement.write_text("Fix the SKU search, using the docs at docs.example.\n")
    package_task(ROOT / TASK_PATH, tmp_path / "treated", replacement)

    shared = SHARED_INSTRUCTIONS.read_text()
    assert (tmp_path / "task/instruction.md").read_text() == (
        f"{(ROOT / TASK_PATH / 'instruction.md').read_text()}\n{shared}"
    )
    assert (tmp_path / "treated/instruction.md").read_text() == (
        f"{replacement.read_text()}\n{shared}"
    )


def test_tasks_get_the_weaviate_settings_unless_they_opt_out():
    # tasks/investigate/db-recommendation opts out; its own test covers that.
    assert compose_overlays(ROOT / TASK_PATH) == [SHARED_COMPOSE, WEAVIATE_COMPOSE]
    assert "WEAVIATE_HTTP_HOST" in WEAVIATE_COMPOSE.read_text()


def test_treatment_files_finds_skills_and_the_tasks_prompt(tmp_path, monkeypatch):
    monkeypatch.setattr(weval.run, "TREATMENTS", tmp_path)
    (tmp_path / "skills-only/skills/a").mkdir(parents=True)
    prompt = tmp_path / "docs-site/prompts/resolve/sku-search.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("Fix the SKU search.\n")

    assert treatment_files("skills-only", TASK_PATH) == (
        tmp_path / "skills-only/skills",
        None,
    )
    assert treatment_files("docs-site", TASK_PATH) == (None, prompt)
    with pytest.raises(FileNotFoundError, match="no prompt for this Task"):
        treatment_files("docs-site", Path("tasks/build/ecommerce-search"))
    with pytest.raises(FileNotFoundError, match="no-such-treatment"):
        treatment_files("no-such-treatment", TASK_PATH)


def test_finalize_records_the_treatment(tmp_path):
    trial = tmp_path / "trial"
    trial.mkdir()
    (trial / "result.json").write_text(
        json.dumps({"verifier_result": {"rewards": {"reward": 1}}})
    )
    oracle = {"name": "oracle", "harness": "oracle"}

    assert finalize(trial, TASK_PATH, oracle)["treatment"] is None
    assert (
        finalize(trial, TASK_PATH, oracle, treatment="weaviate-docs")["treatment"]
        == "weaviate-docs"
    )


def test_fingerprints_version_the_task_and_check_separately(tmp_path):
    task_dir = tmp_path / "sku-search"
    shutil.copytree(
        ROOT / TASK_PATH, task_dir, ignore=shutil.ignore_patterns("__pycache__")
    )
    before = fingerprints(task_dir)

    assert before == fingerprints(ROOT / TASK_PATH)
    assert before["treatment"] is None

    (task_dir / "check.py").write_text("REQUIRED = []\n")
    after_check = fingerprints(task_dir)
    assert after_check["task"] == before["task"]
    assert after_check["check"] != before["check"]

    with (task_dir / "instruction.md").open("a") as prompt:
        prompt.write("One more sentence.\n")
    after_prompt = fingerprints(task_dir)
    assert after_prompt["task"] != before["task"]
    assert after_prompt["check"] == after_check["check"]


def test_a_draft_task_runs_only_with_draft(tmp_path):
    (tmp_path / "task.toml").write_text("[metadata]\ndraft = true\n")

    with pytest.raises(ValueError, match="pass --draft"):
        run(tmp_path, "oracle")
    # With draft, run() gets past the gate and fails later, on this Task
    # sitting outside the repo.
    with pytest.raises(ValueError, match="is not in the subpath"):
        run(tmp_path, "oracle", draft=True)


def test_treatment_fingerprint_covers_the_skills_and_prompt_only(tmp_path):
    task = ROOT / TASK_PATH
    treatment = tmp_path / "treatment"
    shutil.copytree(ROOT / "treatments/weaviate-best-practices", treatment)
    skills = treatment / "skills"
    versions = fingerprints(task, skills)

    (treatment / "README.md").write_text("A different question.\n")
    assert fingerprints(task, skills) == versions

    prompt = treatment / "prompts/resolve/sku-search.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("Fix the SKU search.\n")
    with_prompt = fingerprints(task, skills, prompt)["treatment"]
    assert with_prompt != versions["treatment"]
    prompt.write_text("Fix the SKU search, using docs.example.\n")
    assert fingerprints(task, skills, prompt)["treatment"] != with_prompt

    (skills / "weaviate-best-practices/SKILL.md").write_text("changed\n")
    assert fingerprints(task, skills)["treatment"] != versions["treatment"]


def test_finalize_records_the_fingerprints(tmp_path):
    trial = tmp_path / "trial"
    trial.mkdir()
    (trial / "result.json").write_text(
        json.dumps({"verifier_result": {"rewards": {"reward": 1}}})
    )
    oracle = {"name": "oracle", "harness": "oracle"}
    versions = {"task": "3f9a1c0e2b7d", "check": "a41b07c2d9e3", "treatment": None}

    assert (
        finalize(trial, TASK_PATH, oracle, versions=versions)["fingerprints"]
        == versions
    )
    assert finalize(trial, TASK_PATH, oracle)["fingerprints"] is None


def harbor_result(reward: int | None = None, exception: bool = False) -> dict:
    result: dict = {}
    if reward is not None:
        result["verifier_result"] = {"rewards": {"reward": reward}}
    if exception:
        result["exception_info"] = {"exception_type": "AgentTimeoutError"}
    return result


@pytest.mark.parametrize(
    "result, missing, expected",
    [
        # Harbor raised, nothing graded: infrastructure, not the agent.
        (harbor_result(exception=True), [], "non-result"),
        # Harbor recorded a limit but the verifier still graded the submission.
        (harbor_result(reward=1, exception=True), [], "timed-out"),
        (harbor_result(reward=0, exception=True), [], "timed-out"),
        # No reward at all: infrastructure.
        (harbor_result(), [], "non-result"),
        (harbor_result(reward=1), ["agent/pi.txt"], "incomplete"),
        (harbor_result(reward=1), [], "passed"),
        (harbor_result(reward=0), [], "failed"),
    ],
)
def test_derive_status_truth_table(result, missing, expected):
    assert derive_status(result, missing) == expected


def test_a_session_ended_by_a_model_error_is_a_non_result_even_when_graded():
    for reward in (0, 1):
        assert derive_status(harbor_result(reward=reward), [], "429") == "non-result"


def pi_agent_end(stop_reason: str, error: str | None = None) -> str:
    message = {"role": "assistant", "content": [], "stopReason": stop_reason}
    if error:
        message["errorMessage"] = error
    return json.dumps({"type": "agent_end", "messages": [message]})


def test_finalize_records_the_model_error_that_ended_a_pi_session(tmp_path):
    # Shape from a pi-kimi-k3.1-pro Trial on 2026-10-27: OpenRouter's
    # new-account rate limit failed every attempt, Pi retried and gave up,
    # and the verifier then graded the empty /app as failed.
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "result.json").write_text(json.dumps(harbor_result(reward=0)))
    error = "429: Rate limit exceeded: new-account-rpm/moonshotai/kimi-k3.1-pro"
    (trial / "agent/pi.txt").write_text(
        "\n".join(
            [
                '{"type":"agent_start"}',
                pi_agent_end("error", error),
                '{"type":"auto_retry_start","attempt":3}',
                pi_agent_end("error", error),
                '{"type":"auto_retry_end","success":false}',
                '{"type":"agent_settled"}',
            ]
        )
    )
    agent = {"name": "pi-kimi-k3.1-pro", "harness": "pi", "version": "0.85.1"}

    record = finalize(trial, TASK_PATH, agent)

    assert record["status"] == "non-result"
    assert record["model_error"] == error


def test_a_pi_session_that_recovered_from_a_failed_request_has_no_model_error(
    tmp_path,
):
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "agent/pi.txt").write_text(
        f"{pi_agent_end('error', '429')}\n{pi_agent_end('stop')}\n"
    )
    assert pi.model_error(trial) is None


def test_a_pi_log_cut_off_mid_line_by_the_timeout_still_reads(tmp_path):
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "agent/pi.txt").write_text(
        f'{pi_agent_end("error", "429")}\n{{"type":"turn_start"}}\n{{"type":"message_start","me'
    )
    assert pi.model_error(trial) == "429"


@pytest.mark.parametrize(
    "event, expected",
    [
        # An API error or usage limit ends the session with subtype success.
        (
            {"subtype": "success", "is_error": True, "result": "API Error: 429"},
            "API Error: 429",
        ),
        # The agent used up its turns: its own outcome.
        ({"subtype": "error_max_turns", "is_error": True}, None),
        ({"subtype": "success", "is_error": False, "result": "Done."}, None),
    ],
)
def test_claude_code_model_error_reads_the_final_result_event(
    tmp_path, event, expected
):
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "agent/claude-code.txt").write_text(
        json.dumps({"type": "result", **event}) + "\n"
    )
    assert claude_code.model_error(trial) == expected


@pytest.mark.parametrize("stage", ["stack", "app", "snapshot"])
def test_finalize_records_a_snapshot_error_at_any_stage_as_failed(tmp_path, stage):
    # A "snapshot"-stage error is what a stopped Weaviate gives a Task with
    # WEVAL_KEEP_STACK, such as deploy/local-instance.
    trial = tmp_path / "trial"
    (trial / "verifier").mkdir(parents=True)
    (trial / "agent").mkdir()
    (trial / "artifacts/submission").mkdir(parents=True)
    (trial / "agent/oracle.txt").write_text("")
    (trial / "result.json").write_text(json.dumps(harbor_result(reward=0)))
    (trial / "verifier/snapshot.json").write_text(
        json.dumps({"error": "Traceback: Connection refused", "error_stage": stage})
    )
    (trial / "verifier/checks.json").write_text("[]")

    record = finalize(trial, TASK_PATH, {"name": "oracle", "harness": "oracle"})

    assert record["status"] == "failed"
    assert record["error_stage"] == stage


def test_finalize_run_records_the_other_trials_past_an_unreadable_one(tmp_path):
    job = tmp_path / "job"
    graded = job / "trial-0"
    (graded / "verifier").mkdir(parents=True)
    (graded / "result.json").write_text(json.dumps(harbor_result(reward=1)))
    shutil.copy(ORACLE_SNAPSHOT, graded / "verifier/snapshot.json")
    truncated = job / "trial-1"
    truncated.mkdir()
    (truncated / "result.json").write_text('{"verifier_result": {"rew')

    finalize_run(tmp_path, TASK_PATH, {"name": "oracle", "harness": "oracle"}, 2)

    assert json.loads((graded / "weval.json").read_text())["reward"] == 1
    stub = json.loads((truncated / "weval.json").read_text())
    assert stub["status"] == "non-result"
    assert stub["exception"].startswith("recording failed: JSONDecodeError")


def test_finalize_run_records_a_trial_without_result_json(tmp_path, capsys):
    job = tmp_path / "job"
    graded = job / "trial-0"
    (graded / "verifier").mkdir(parents=True)
    (graded / "result.json").write_text(json.dumps(harbor_result(reward=1)))
    shutil.copy(ORACLE_SNAPSHOT, graded / "verifier/snapshot.json")
    (job / "trial-1").mkdir()

    versions = {"task": "3f9a1c0e2b7d", "check": "a41b07c2d9e3", "treatment": None}
    finalize_run(
        tmp_path,
        TASK_PATH,
        {"name": "oracle", "harness": "oracle"},
        attempts=3,
        versions=versions,
    )

    assert json.loads((graded / "weval.json").read_text())["fingerprints"] == versions
    stub = json.loads((job / "trial-1/weval.json").read_text())
    assert stub["status"] == "non-result"
    assert stub["exception"] == "result.json never written"
    assert stub["fingerprints"] == versions
    out = capsys.readouterr().out
    assert "trial-0" in out and "trial-1" in out
    assert "3 Trials requested, 2 found" in out
