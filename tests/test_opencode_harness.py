"""The OpenCode harness builds a Harbor config that resolves to Harbor's
OpenCode agent, for every OpenCode Agent in agents.toml."""

import importlib
import json
import tomllib

from conftest import ROOT
from harbor.agents.installed.opencode import OpenCode

from weval.harnesses import opencode

AGENTS = {
    name: agent
    for name, agent in tomllib.loads((ROOT / "agents.toml").read_text()).items()
    if agent["harness"] == "opencode"
}


def test_agents_toml_has_an_opencode_agent():
    assert AGENTS


def test_config_resolves_to_harbor_opencode_with_the_pinned_version():
    for agent in AGENTS.values():
        config = opencode.agent_config(agent)
        module, _, name = config.import_path.partition(":")

        assert getattr(importlib.import_module(module), name) is OpenCode
        assert config.kwargs == {
            "version": agent["version"],
            "opencode_config": {"snapshot": False},
        }
        # OpenCode refuses a model name without a provider prefix.
        assert config.model_name.startswith("openrouter/")
        assert config.env == {"OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}"}


def test_token_usage_counts_reasoning_as_output(tmp_path):
    # Shapes from a real Trial: the tool-call step reports its completion
    # tokens as reasoning, with output 0.
    def step(output, reasoning):
        tokens = {"input": 1, "output": output, "reasoning": reasoning}
        return json.dumps({"type": "step_finish", "part": {"tokens": tokens}})

    log = tmp_path / "agent/opencode.txt"
    log.parent.mkdir()
    log.write_text(
        "error: EPIPE: broken pipe, write\n"
        + "\n".join([step(0, 7498), step(86, 0), step(98, 0)])
    )

    assert opencode.token_usage(tmp_path) == {"n_output_tokens": 7682}


def test_token_usage_keeps_harbor_figures_without_steps(tmp_path):
    assert opencode.token_usage(tmp_path) == {}
