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
    """Return token counts summed from OpenCode's ``step_finish`` events.

    Field names match ``weval.json``'s: ``n_input_tokens`` includes cache
    reads and cache writes, which ``n_cache_tokens`` and
    ``n_cache_creation_tokens`` break out, and ``n_output_tokens`` includes
    reasoning tokens. Pi and Claude Code count both that way. Harbor's
    figures drop cache writes from input and reasoning from output, which
    OpenCode reports separately in ``agent/opencode.txt``. Harbor's
    ``cost_usd`` is OpenCode's own and is kept. Returns ``{}`` when there is
    no ``step_finish`` event.
    """
    log = trial_dir / "agent/opencode.txt"
    lines = log.read_text().splitlines() if log.exists() else []
    events = [json.loads(line) for line in lines if line.startswith("{")]
    steps = [e["part"]["tokens"] for e in events if e.get("type") == "step_finish"]
    if not steps:
        return {}
    cache_read = sum(t["cache"]["read"] for t in steps)
    cache_write = sum(t["cache"]["write"] for t in steps)
    return {
        "n_input_tokens": sum(t["input"] for t in steps) + cache_read + cache_write,
        "n_cache_tokens": cache_read,
        "n_cache_creation_tokens": cache_write,
        "n_output_tokens": sum(t["output"] + t["reasoning"] for t in steps),
    }
