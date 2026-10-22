"""Harbor's built-in Claude Code, with inference through OpenRouter or a Claude subscription.

By default, Claude Code authenticates to OpenRouter's Anthropic-compatible
endpoint with the OpenRouter key as a bearer token; ``ANTHROPIC_API_KEY`` is set
empty so it cannot fall back to Anthropic directly. An Agent with
``auth = "subscription"`` instead calls Anthropic with the long-lived OAuth
token from ``claude setup-token`` in ``CLAUDE_CODE_OAUTH_TOKEN``, and its
``model`` is an Anthropic model ID such as ``anthropic/claude-opus-5-5``.
Harbor sets every model alias, including the subagent model, to the Agent's
``model``.

Claude Code is installed from a binary the host downloads once per version and
platform (``CachedClaudeCode``), not by Harbor's per-Trial download.
"""

import asyncio
import gzip
import hashlib
import json
import os
import shlex
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import override

from harbor.agents.installed.claude_code import ClaudeCode
from harbor.environments.base import BaseEnvironment
from harbor.models.trial.config import AgentConfig

# Relative to the Harbor Trial directory. A missing match marks the Trial incomplete.
EXPECTED_LOGS = (
    "agent/claude-code.txt",
    "agent/sessions/projects/*/*.jsonl",
)


def agent_config(agent: dict) -> AgentConfig:
    """Build Harbor's agent config for a Claude Code Agent (``version``, ``model``, optional ``auth``)."""
    # Harbor resolves the templates from the host environment.
    if agent.get("auth") == "subscription":
        # The empty key overrides any host ANTHROPIC_API_KEY, which Claude Code
        # would prefer to the token. Harbor's CLAUDE_FORCE_OAUTH flag does the
        # same, but Harbor treats its value "1" as a secret and scrubs every "1"
        # from the Trial output.
        env = {"CLAUDE_CODE_OAUTH_TOKEN": "${CLAUDE_CODE_OAUTH_TOKEN}", "ANTHROPIC_API_KEY": ""}
    else:
        env = {
            "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
            "ANTHROPIC_AUTH_TOKEN": "${OPENROUTER_API_KEY}",
            "ANTHROPIC_API_KEY": "",
        }
    return AgentConfig(
        import_path=f"{__name__}:CachedClaudeCode",
        model_name=agent["model"],
        kwargs={"version": agent["version"]},
        env=env,
    )


RELEASES = "https://downloads.claude.ai/claude-code-releases"
# One gzipped binary per version and platform, kept across runs.
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "weval/claude-code"
REMOTE_ARCHIVE = "/tmp/weval-claude.gz"
# The platform names of Claude Code's release manifest, detected as bootstrap.sh does.
PLATFORM_COMMAND = (
    'case "$(uname -m)" in x86_64|amd64) arch=x64 ;; arm64|aarch64) arch=arm64 ;; *) arch="$(uname -m)" ;; esac; '
    "if [ -f /lib/libc.musl-x86_64.so.1 ] || [ -f /lib/libc.musl-aarch64.so.1 ] "
    "|| ldd /bin/ls 2>&1 | grep -q musl; then echo linux-$arch-musl; else echo linux-$arch; fi"
)
# Concurrent Trials in one run share a single download.
_download_lock = asyncio.Lock()


class CachedClaudeCode(ClaudeCode):
    """Harbor's Claude Code agent, installed from the host's cached binary.

    Harbor's own install downloads Claude Code from downloads.claude.ai inside
    every Trial, and concurrent Trials on Modal get HTTP 429 from it. This
    install uploads the binary from ``CACHE_DIR`` instead, downloading it on
    the host first if needed, then lets Harbor's install confirm the version.
    The Trial environment gets the same system packages as Harbor's install.
    """

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        if not self._version:
            raise ValueError("a Claude Code Agent needs a version to install from the cache")
        await self.ensure_system_dependencies(environment, ("curl", "bash", "nodejs", "npm", "procps"))
        platform = (await environment.exec(command=PLATFORM_COMMAND)).stdout.strip()
        async with _download_lock:
            archive = await asyncio.to_thread(cached_binary, self._version, platform)

        await self._upload_agent_owned_file(environment, archive, REMOTE_ARCHIVE)
        # As bootstrap.sh does, the binary's own `claude install` links
        # ~/.local/bin/claude and writes ~/.claude.json (native install, auto-updates
        # off). It finds the requested version already in place, so it downloads nothing.
        binary = f"~/.local/share/claude/versions/{shlex.quote(self._version)}"
        await self.exec_as_agent(
            environment,
            command=(
                "set -eu; mkdir -p ~/.local/share/claude/versions; "
                f"gunzip -c {REMOTE_ARCHIVE} > {binary}; chmod +x {binary}; rm -f {REMOTE_ARCHIVE}; "
                f"{binary} install {shlex.quote(self._version)}; "
                "echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc"
            ),
        )
        # Finds the requested version and returns; it downloads only on a mismatch.
        await super().install(environment)


def cached_binary(version: str, platform: str) -> Path:
    """Return the gzipped Claude Code binary for ``version`` and ``platform``
    (a release-manifest name such as ``linux-x64``), downloading it into
    ``CACHE_DIR`` and checking it against the manifest's SHA-256 first if
    it is not cached."""
    archive = CACHE_DIR / version / f"claude-{platform}.gz"
    if archive.exists():
        return archive

    manifest = json.loads(_fetch(f"{RELEASES}/{version}/manifest.json"))
    if platform not in manifest["platforms"]:
        raise ValueError(f"Claude Code {version} has no {platform!r} build")
    binary = _fetch(f"{RELEASES}/{version}/{platform}/claude")
    expected = manifest["platforms"][platform]["checksum"]
    if hashlib.sha256(binary).hexdigest() != expected:
        raise RuntimeError(f"Claude Code {version} {platform} does not match the manifest checksum")

    archive.parent.mkdir(parents=True, exist_ok=True)
    # Written under another name first so an interrupted write is never taken as cached.
    partial = archive.with_name(archive.name + ".partial")
    with gzip.open(partial, "wb", compresslevel=6) as file:
        file.write(binary)
    partial.replace(archive)
    return archive


def _fetch(url: str, retries: int = 2) -> bytes:
    """GET ``url``, retrying a failed request after 10 s, then 20 s."""
    for retry in range(retries):
        try:
            return _get(url)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(10 * 2**retry)
    return _get(url)


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=300) as response:
        return response.read()


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
