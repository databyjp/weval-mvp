"""``weval.json`` records the Task path relative to the repository, and
``weval check`` resolves it from there, whatever the working directory."""

import json
import shutil
from pathlib import Path

from weval.run import ROOT, finalize, rescore

TASK_PATH = Path("tasks/resolve/sku-search")
ORACLE_SNAPSHOT = ROOT / "tests/fixtures/resolve-sku-search-oracle-snapshot.json"


def test_finalize_records_task_path_and_rescore_resolves_it(tmp_path, monkeypatch):
    trial = tmp_path / "trial"
    (trial / "verifier").mkdir(parents=True)
    (trial / "result.json").write_text(json.dumps({"verifier_result": {"rewards": {"reward": 1}}}))
    shutil.copy(ORACLE_SNAPSHOT, trial / "verifier/snapshot.json")

    record = finalize(trial, TASK_PATH, {"name": "oracle", "harness": "oracle"})
    assert record["task"] == "tasks/resolve/sku-search"

    monkeypatch.chdir(tmp_path)
    results = rescore(trial)
    assert results and all(r["passed"] for r in results)


def test_finalize_records_usage_from_result_and_trajectory(tmp_path):
    # Tool-call shapes copied from retained Pi Trials: a web search, a fetch,
    # and curl in bash, plus a probe of the Trial's own Weaviate.
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "result.json").write_text(json.dumps({"agent_result": {
        "n_input_tokens": 1080469, "n_cache_tokens": 1023424,
        "n_output_tokens": 33356, "cost_usd": 0.028,
    }}))
    calls = [
        ("web_search", {"queries": ["Weaviate latest stable version", "weaviate-client latest"]}),
        ("fetch_content", {"url": "https://docs.weaviate.io/deploy/migration"}),
        ("bash", {"command": 'curl -s "https://api.github.com/repos/weaviate/weaviate/releases?per_page=15"'}),
        ("bash", {"command": "curl -s http://weaviate:8080/v1/meta && curl http://127.0.0.1:8000/search"}),
        ("fetch_content", {"url": "https://docs.weaviate.io/deploy/migration"}),
    ]
    (trial / "agent/trajectory.json").write_text(json.dumps({"steps": [
        {"tool_calls": [{"function_name": name, "arguments": arguments}]} for name, arguments in calls
    ]}))

    usage = finalize(trial, TASK_PATH, {"name": "oracle", "harness": "oracle"})["usage"]

    assert usage == {
        "n_input_tokens": 1080469, "n_cache_tokens": 1023424,
        "n_output_tokens": 33356, "cost_usd": 0.028,
        "tool_calls": {"web_search": 1, "fetch_content": 2, "bash": 2},
        "urls": [
            "https://docs.weaviate.io/deploy/migration",
            "https://api.github.com/repos/weaviate/weaviate/releases?per_page=15",
        ],
        "search_queries": ["Weaviate latest stable version", "weaviate-client latest"],
    }


def test_finalize_takes_claude_code_tokens_from_its_model_usage(tmp_path):
    # Figures from Trial 20261016-105100 (claude-code-haiku-5.5): Harbor's
    # counts miss the requests in which WebFetch summarises each page.
    trial = tmp_path / "trial"
    (trial / "agent").mkdir(parents=True)
    (trial / "result.json").write_text(json.dumps({"agent_result": {
        "n_input_tokens": 437709, "n_cache_tokens": 383347,
        "n_output_tokens": 10094, "cost_usd": 2.235776,
    }}))
    final_event = {"type": "result", "modelUsage": {"anthropic/claude-haiku-5.5": {
        "inputTokens": 163888, "outputTokens": 35401, "cacheReadInputTokens": 383347,
        "cacheCreationInputTokens": 54342, "costUSD": 2.235776, "costBasis": "unknown",
    }}}
    (trial / "agent/claude-code.txt").write_text(f'{{"type": "system"}}\n{json.dumps(final_event)}\n')

    agent = {"name": "claude-code-haiku-5.5", "harness": "claude-code"}
    usage = finalize(trial, TASK_PATH, agent)["usage"]

    assert {k: usage[k] for k in ("n_input_tokens", "n_cache_tokens", "n_cache_creation_tokens",
                                  "n_output_tokens", "cost_usd")} == {
        "n_input_tokens": 601577, "n_cache_tokens": 383347, "n_cache_creation_tokens": 54342,
        "n_output_tokens": 35401, "cost_usd": None,
    }
