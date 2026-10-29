"""Harbor's built-in OpenCode, with inference through OpenRouter.

OpenCode reads ``OPENROUTER_API_KEY`` for ``openrouter/`` models, and Harbor
registers the Agent's model with OpenCode's ``openrouter`` provider. The agent
has OpenCode's own ``webfetch`` and ``websearch`` tools, so it reads pages
differently from Pi's ``pi-web-access`` and Claude Code's ``WebFetch``.

Harness protocol members are documented in ``weval.harnesses``.
"""

import json
from pathlib import Path

from harbor.models.trial.config import AgentConfig

# Relative to the Harbor Trial directory. A missing match marks the Trial incomplete.
EXPECTED_LOGS = (
    "agent/opencode.txt",
    "agent/trajectory.json",
)


def agent_config(agent: dict) -> AgentConfig:
    """Build Harbor's agent config for an OpenCode Agent (``version``, ``model``)."""
    return AgentConfig(
        import_path="harbor.agents.installed.opencode:OpenCode",
        model_name=agent["model"],
        kwargs={
            "version": agent["version"],
            # Harbor sets OPENCODE_FAKE_VCS=git, so OpenCode snapshots /app
            # with git at every step. Writing to an exited git child raises
            # EPIPE and the run exits 1 after a completed session. Harbor
            # then reports a failure, often misclassified as an API error
            # from text in the stream. Snapshots only serve OpenCode's undo.
            "opencode_config": {"snapshot": False},
        },
        # Harbor resolves the template from the host environment.
        env={"OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}"},
    )


def agent_record(agent: dict) -> dict:
    return dict(agent)


def token_usage(trial_dir: Path) -> dict:
    """Return ``n_output_tokens`` with reasoning tokens counted as output.

    OpenCode's ``step_finish`` events in ``agent/opencode.txt`` split
    completion tokens into ``output`` and ``reasoning``, and Harbor keeps
    only ``output``. Pi and Claude Code count reasoning inside output, so
    this keeps OpenCode's figure comparable with theirs. Harbor's input,
    cache, and cost figures already match OpenCode's and are kept. Returns
    ``{}`` when there is no ``step_finish`` event.
    """
    log = trial_dir / "agent/opencode.txt"
    lines = log.read_text().splitlines() if log.exists() else []
    events = [json.loads(line) for line in lines if line.startswith("{")]
    steps = [e["part"]["tokens"] for e in events if e.get("type") == "step_finish"]
    if not steps:
        return {}
    return {"n_output_tokens": sum(t["output"] + t["reasoning"] for t in steps)}
