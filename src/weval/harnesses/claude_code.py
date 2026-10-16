"""Harbor's built-in Claude Code, with inference routed through OpenRouter.

Claude Code authenticates to OpenRouter's Anthropic-compatible endpoint with
the OpenRouter key as a bearer token; ``ANTHROPIC_API_KEY`` is set empty so it
cannot fall back to Anthropic directly. Harbor sets every model alias, including
the subagent model, to the Agent's ``model``.
"""

import json
from pathlib import Path

from harbor.models.trial.config import AgentConfig

# Relative to the Harbor Trial directory. A missing match marks the Trial incomplete.
EXPECTED_LOGS = (
    "agent/claude-code.txt",
    "agent/sessions/projects/*/*.jsonl",
)


def agent_config(agent: dict) -> AgentConfig:
    """Build Harbor's agent config for a Claude Code Agent (``version``, ``model``)."""
    return AgentConfig(
        name="claude-code",
        model_name=agent["model"],
        kwargs={"version": agent["version"]},
        env={
            "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
            # Harbor resolves the template from the host environment.
            "ANTHROPIC_AUTH_TOKEN": "${OPENROUTER_API_KEY}",
            "ANTHROPIC_API_KEY": "",
        },
    )


def agent_record(agent: dict) -> dict:
    return dict(agent)


def token_usage(trial_dir: Path) -> dict:
    """Return token counts and cost from Claude Code's own ``modelUsage``.

    Harbor's counts cover only the main conversation. ``modelUsage``, in the
    final ``result`` event of ``agent/claude-code.txt``, also covers the
    separate requests in which ``WebFetch`` summarises each page. Field names
    match ``weval.json``'s: ``n_input_tokens`` includes cache reads and cache
    writes, which ``n_cache_tokens`` and ``n_cache_creation_tokens`` break out.
    ``cost_usd`` is ``None`` when Claude Code has no price for a model, as for
    OpenRouter model names. Returns ``{}``, keeping Harbor's figures, when
    there is no ``result`` event.
    """
    log = trial_dir / "agent/claude-code.txt"
    lines = log.read_text().splitlines() if log.exists() else []
    events = [json.loads(line) for line in lines if line.startswith("{")]
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result is None or not result.get("modelUsage"):
        return {}
    models = result["modelUsage"].values()

    def total(key: str) -> int:
        return sum(m.get(key, 0) for m in models)

    return {
        "n_input_tokens": total("inputTokens") + total("cacheReadInputTokens")
        + total("cacheCreationInputTokens"),
        "n_cache_tokens": total("cacheReadInputTokens"),
        "n_cache_creation_tokens": total("cacheCreationInputTokens"),
        "n_output_tokens": total("outputTokens"),
        "cost_usd": None if any(m.get("costBasis") == "unknown" for m in models)
        else sum(m.get("costUSD", 0) for m in models),
    }
