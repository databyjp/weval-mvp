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
platform (``CachedClaudeCode``), not by Harbor's per-Trial download. Modal
Trials read it from a Modal Volume (``modal_environment``).

Harness protocol members are documented in ``weval.harnesses``.
"""

import asyncio
import fcntl
import gzip
import hashlib
import json
import os
import re
import shlex
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import override

import modal
from harbor.agents.installed.claude_code import ClaudeCode
from harbor.environments.base import BaseEnvironment
from harbor.models.trial.config import AgentConfig, EnvironmentConfig

# Relative to the Harbor Trial directory. A missing match marks the Trial incomplete.
EXPECTED_LOGS = (
    "agent/claude-code.txt",
    "agent/sessions/projects/*/*.jsonl",
)
# USD per million tokens, by modelUsage field, from OpenRouter's model list on
# 2026-10-22 (cache writes at the 5-minute rate). Claude Code's own costUSD uses
# other prices, and has none for Haiku 5.5. WebFetch summarises pages with
# Haiku 4.5 whatever the Agent's model.
PRICES = {
    "claude-haiku-5-5": {
        "inputTokens": 0.10,
        "outputTokens": 0.50,
        "cacheReadInputTokens": 0.01,
        "cacheCreationInputTokens": 0.125,
    },
    "claude-sonnet-5-5": {
        "inputTokens": 2.00,
        "outputTokens": 10.00,
        "cacheReadInputTokens": 0.10,
        "cacheCreationInputTokens": 2.50,
    },
    "claude-opus-5-5": {
        "inputTokens": 4.00,
        "outputTokens": 20.00,
        "cacheReadInputTokens": 0.20,
        "cacheCreationInputTokens": 5.00,
    },
    "claude-haiku-4-5": {
        "inputTokens": 1.00,
        "outputTokens": 5.00,
        "cacheReadInputTokens": 0.10,
        "cacheCreationInputTokens": 1.25,
    },
}


def agent_config(agent: dict) -> AgentConfig:
    """Build Harbor's agent config for a Claude Code Agent (``version``, ``model``, optional ``auth``)."""
    # Harbor resolves the templates from the host environment.
    if agent.get("auth") == "subscription":
        # The empty key overrides any host ANTHROPIC_API_KEY, which Claude Code
        # would prefer to the token. Harbor's CLAUDE_FORCE_OAUTH flag does the
        # same, but Harbor treats its value "1" as a secret and scrubs every "1"
        # from the Trial output.
        env = {
            "CLAUDE_CODE_OAUTH_TOKEN": "${CLAUDE_CODE_OAUTH_TOKEN}",
            "ANTHROPIC_API_KEY": "",
        }
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
CACHE_DIR = (
    Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    / "weval/claude-code"
)
REMOTE_ARCHIVE = "/tmp/weval-claude.gz"
# The Modal Volume holds the same layout as CACHE_DIR, mounted read-only at
# VOLUME_MOUNT in the agent's container.
VOLUME = "weval-claude-code"
VOLUME_MOUNT = "/opt/weval/claude-code"
MODAL_PLATFORM = "linux-x64"
# The platform names of Claude Code's release manifest, detected as bootstrap.sh does.
PLATFORM_COMMAND = (
    'case "$(uname -m)" in x86_64|amd64) arch=x64 ;; arm64|aarch64) arch=arm64 ;; *) arch="$(uname -m)" ;; esac; '
    "if [ -f /lib/libc.musl-x86_64.so.1 ] || [ -f /lib/libc.musl-aarch64.so.1 ] "
    "|| ldd /bin/ls 2>&1 | grep -q musl; then echo linux-$arch-musl; else echo linux-$arch; fi"
)


class CachedClaudeCode(ClaudeCode):
    """Harbor's Claude Code agent, installed from the host's cached binary.

    Harbor's own install downloads Claude Code from downloads.claude.ai inside
    every Trial, and concurrent Trials on Modal get HTTP 429 from it. This
    install reads the binary from the Modal Volume when it is mounted, and
    otherwise uploads it from ``CACHE_DIR``, downloading it on the host first
    if needed. Harbor's install then confirms the version. The Trial
    environment gets the same system packages as Harbor's install.
    """

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        if not self._version:
            raise ValueError(
                "a Claude Code Agent needs a version to install from the cache"
            )
        await self.ensure_system_dependencies(
            environment, ("curl", "bash", "nodejs", "npm", "procps")
        )
        platform = (await environment.exec(command=PLATFORM_COMMAND)).stdout.strip()
        archive = f"{VOLUME_MOUNT}/{shlex.quote(self._version)}/claude-{platform}.gz"
        if (await environment.exec(command=f"test -f {archive}")).return_code != 0:
            cached = await asyncio.to_thread(cached_binary, self._version, platform)
            await self._upload_agent_owned_file(environment, cached, REMOTE_ARCHIVE)
            archive = REMOTE_ARCHIVE

        # As bootstrap.sh does, the binary's own `claude install` links
        # ~/.local/bin/claude and writes ~/.claude.json (native install, auto-updates
        # off). It finds the requested version already in place, so it downloads nothing.
        binary = f"~/.local/share/claude/versions/{shlex.quote(self._version)}"
        await self.exec_as_agent(
            environment,
            command=(
                "set -eu; mkdir -p ~/.local/share/claude/versions; "
                f"gunzip -c {archive} > {binary}; chmod +x {binary}; rm -f {REMOTE_ARCHIVE}; "
                f"{binary} install {shlex.quote(self._version)}; "
                "echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc"
            ),
        )
        # Finds the requested version and returns; it downloads only on a mismatch.
        await super().install(environment)


def modal_environment(agent: dict, environment: EnvironmentConfig) -> EnvironmentConfig:
    """Return ``environment`` with the ``VOLUME`` Modal Volume mounted
    read-only at ``VOLUME_MOUNT`` in the agent's container, after uploading
    the Agent's ``linux-x64`` binary to it if the Volume lacks it."""
    publish_to_volume(agent["version"])
    # Harbor binds a mount's target path on the sandbox VM, where Modal mounts the Volume.
    mount = {
        "type": "bind",
        "source": VOLUME_MOUNT,
        "target": VOLUME_MOUNT,
        "read_only": True,
    }
    return environment.model_copy(
        update={
            "kwargs": {**environment.kwargs, "volumes": {VOLUME_MOUNT: VOLUME}},
            "mounts": [*(environment.mounts or []), mount],
        }
    )


def publish_to_volume(version: str) -> None:
    """Upload ``version``'s ``MODAL_PLATFORM`` binary from the host cache to
    the ``VOLUME`` Modal Volume, creating the Volume if needed. Does nothing
    when the Volume already holds it."""
    # Before any sandbox starts: a running sandbox does not see later uploads.
    volume = modal.Volume.from_name(VOLUME, create_if_missing=True)
    remote = f"{version}/claude-{MODAL_PLATFORM}.gz"
    with _host_lock(version, "volume"):
        try:
            if any(
                entry.path.strip("/") == remote for entry in volume.listdir(version)
            ):
                return
        except modal.exception.NotFoundError:
            pass
        try:
            with volume.batch_upload() as batch:
                batch.put_file(cached_binary(version, MODAL_PLATFORM), f"/{remote}")
        except FileExistsError:
            pass  # A run on another host uploaded it first.


def cached_binary(version: str, platform: str) -> Path:
    """Return the gzipped Claude Code binary for ``version`` and ``platform``
    (a release-manifest name such as ``linux-x64``), downloading it into
    ``CACHE_DIR`` and checking it against the manifest's SHA-256 first if
    it is not cached. Concurrent callers on this host wait for one download."""
    archive = CACHE_DIR / version / f"claude-{platform}.gz"
    with _host_lock(version, "download"):
        if archive.exists():
            return archive

        manifest = json.loads(_fetch(f"{RELEASES}/{version}/manifest.json"))
        if platform not in manifest["platforms"]:
            raise ValueError(f"Claude Code {version} has no {platform!r} build")
        binary = _fetch(f"{RELEASES}/{version}/{platform}/claude")
        expected = manifest["platforms"][platform]["checksum"]
        if hashlib.sha256(binary).hexdigest() != expected:
            raise RuntimeError(
                f"Claude Code {version} {platform} does not match the manifest checksum"
            )

        # Written under another name first so an interrupted write is never taken as cached.
        partial = archive.with_name(archive.name + ".partial")
        with gzip.open(partial, "wb", compresslevel=6) as file:
            file.write(binary)
        partial.replace(archive)
        return archive


@contextmanager
def _host_lock(version: str, name: str) -> Iterator[None]:
    """Hold ``CACHE_DIR/<version>/<name>.lock`` exclusively against every
    other process and thread on this host."""
    # flock locks belong to the open file, so separate opens exclude each other
    # within one process too, and the OS releases a dead holder's lock.
    lock = CACHE_DIR / version / f"{name}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "w") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        yield


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
    ``cost_usd`` is an estimate from ``PRICES``, and ``None`` when a model
    has no entry there. Returns ``{}``, keeping Harbor's figures, when there
    is no ``result`` event.
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
        "n_input_tokens": total("inputTokens")
        + total("cacheReadInputTokens")
        + total("cacheCreationInputTokens"),
        "n_cache_tokens": total("cacheReadInputTokens"),
        "n_cache_creation_tokens": total("cacheCreationInputTokens"),
        "n_output_tokens": total("outputTokens"),
        "cost_usd": cost_usd(result["modelUsage"]),
    }


def cost_usd(model_usage: dict) -> float | None:
    """Estimate the OpenRouter cost of one Trial's ``modelUsage`` from
    ``PRICES``; ``None`` when any model has no entry. Haiku 5.5's higher
    rate for prompts over 100k tokens is not applied, so its estimate is a
    lower bound."""
    cost = 0.0
    for name, usage in model_usage.items():
        # Keys are OpenRouter names in older Trials, e.g.
        # "anthropic/claude-haiku-5.5", and dated Anthropic IDs in newer ones.
        model = re.sub(
            r"^anthropic/|-\d{8}$", "", usage.get("canonicalModel", name)
        ).replace(".", "-")
        if model not in PRICES:
            return None
        cost += (
            sum(usage.get(field, 0) * price for field, price in PRICES[model].items())
            / 1e6
        )
    return cost
