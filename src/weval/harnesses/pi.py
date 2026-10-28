"""Pi with the pinned ``pi-web-access`` extension for web search and fetch.

``WebAccessPi`` extends Harbor's Pi adapter: after Harbor installs Pi, it
installs ``pi-web-access`` with ``npm ci`` from the pinned lockfile in
``pi_web_access/`` and fails setup unless the exact pinned version resolved.
Copies of the lockfile, search config, and provenance go to ``/logs/agent`` so
each Trial records the web tooling it ran with.

Harness protocol members are documented in ``weval.harnesses``.
"""

import json
import shlex
from pathlib import Path, PurePosixPath
from typing import Annotated, override

from harbor.agents.installed.pi import Pi, PiOptions
from harbor.agents.options import Cli
from harbor.environments.base import BaseEnvironment
from harbor.models.trial.config import AgentConfig

ASSETS = Path(__file__).with_name("pi_web_access")
WEB_ACCESS_VERSION: str = json.loads((ASSETS / "package.json").read_text())[
    "dependencies"
]["pi-web-access"]

_PACKAGE_DIR = PurePosixPath("/tmp/harbor-pi-web-access")
# Harbor's Pi adapter also uses this config dir; web-search.json must live here.
_CONFIG_DIR = PurePosixPath("/tmp/harbor-pi-agent")
_EXTENSION = _PACKAGE_DIR / "node_modules/pi-web-access/dist/index.js"
_AGENT_LOGS = PurePosixPath("/logs/agent")

# Relative to the Harbor Trial directory. A missing match marks the Trial incomplete.
EXPECTED_LOGS = (
    "agent/pi.txt",
    "agent/pi/sessions/*.jsonl",
    "agent/web-access.json",
    "agent/web-search.json",
    "agent/pi-web-access-package-lock.json",
)


def agent_config(agent: dict) -> AgentConfig:
    """Build Harbor's agent config for a Pi Agent (``version``, ``model``)."""
    return AgentConfig(
        import_path="weval.harnesses.pi:WebAccessPi",
        model_name=agent["model"],
        kwargs={"version": agent["version"]},
        env={
            # Harbor resolves the template from the host environment.
            "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
            "PI_CODING_AGENT_DIR": _CONFIG_DIR.as_posix(),
        },
    )


def model_error(trial_dir: Path) -> str | None:
    """The error of Pi's last model request, when the session ended on it.

    Pi retries a failed request itself; once it gives up, the final
    ``agent_end`` event in ``agent/pi.txt`` ends on a message with
    ``stopReason`` ``error``, as when OpenRouter rate-limited every attempt.
    """
    log = trial_dir / "agent/pi.txt"
    lines = log.read_text().splitlines() if log.exists() else []
    events = [json.loads(line) for line in lines if line.startswith("{")]
    end = next((e for e in reversed(events) if e.get("type") == "agent_end"), None)
    last = ((end or {}).get("messages") or [{}])[-1]
    if last.get("stopReason") != "error":
        return None
    return last.get("errorMessage") or "model request failed"


def agent_record(agent: dict) -> dict:
    """Return the Agent plus the web tooling it ran with, for ``weval.json``."""
    return {**agent, "web_access": json.loads((ASSETS / "provenance.json").read_text())}


class _Options(PiOptions):
    web_access_extension: Annotated[str, Cli("--extension")] = _EXTENSION.as_posix()


class WebAccessPi(Pi):
    """Harbor's Pi plus the pinned ``pi-web-access`` extension."""

    options_model = _Options

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        """Install Pi and the pinned extension; fail if the version does not match."""
        await super().install(environment)
        dirs = " ".join(
            shlex.quote(str(d)) for d in (_PACKAGE_DIR, _CONFIG_DIR, _AGENT_LOGS)
        )
        await self.exec_as_agent(environment, command=f"mkdir -p {dirs}")
        for name, remote in (
            ("package.json", _PACKAGE_DIR / "package.json"),
            ("package-lock.json", _PACKAGE_DIR / "package-lock.json"),
            ("web-search.json", _CONFIG_DIR / "web-search.json"),
            ("package-lock.json", _AGENT_LOGS / "pi-web-access-package-lock.json"),
            ("web-search.json", _AGENT_LOGS / "web-search.json"),
            ("provenance.json", _AGENT_LOGS / "web-access.json"),
        ):
            await self._upload_config_text(
                environment,
                content=(ASSETS / name).read_text(),
                remote_path=remote.as_posix(),
                filename=name,
            )
        # npm ci enforces the lockfile; --ignore-scripts skips package install hooks.
        await self.exec_as_agent(
            environment,
            command=(
                ". ~/.nvm/nvm.sh && npm ci --ignore-scripts --omit=dev --omit=peer "
                f"--legacy-peer-deps --no-audit --no-fund --prefix {shlex.quote(str(_PACKAGE_DIR))}"
            ),
        )
        manifest = _PACKAGE_DIR / "node_modules/pi-web-access/package.json"
        version_check = (
            f"if(require({json.dumps(str(manifest))}).version!=={json.dumps(WEB_ACCESS_VERSION)})"
            "process.exit(1)"
        )
        await self.exec_as_agent(
            environment,
            command=(
                f". ~/.nvm/nvm.sh && test -f {shlex.quote(str(_EXTENSION))} "
                f"&& node -e {shlex.quote(version_check)}"
            ),
        )
