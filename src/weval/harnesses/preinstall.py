"""Installing an Agent into the Trial image instead of at every Trial's setup.

Harbor's installed agents download their tooling (apt packages, nvm and Node,
npm packages) in every Trial's setup, and a slow or failing network then ends
the Trial before the agent starts. A harness's ``image_layer`` appends the same
installation to the packaged Task's Dockerfile. Docker caches the layer, so a
host builds it once per Task image and Agent version. The harness's
``install`` skips Harbor's installation when ``is_preinstalled`` finds the
pinned version, and falls back to it otherwise.
"""

import json
import shlex
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from harbor.agents.installed.base import BaseInstalledAgent
from harbor.environments.base import BaseEnvironment

# The build-context directory that holds an ImageLayer's files.
CONTEXT_DIR = "weval-agent"


@dataclass(frozen=True)
class ImageLayer:
    """Dockerfile instructions that install one Agent into the Trial image.

    ``instructions`` run after the Task's own Dockerfile, as root with
    ``HOME=/root``, the user and home directory Harbor runs the agent with.
    ``files`` maps a path under ``CONTEXT_DIR`` in the build context, which
    ``instructions`` COPY from, to its source on the host.
    """

    instructions: str
    files: Mapping[str, Path] = field(default_factory=dict)

    def add_to(self, environment_dir: Path) -> None:
        """Append the layer to the packaged Task environment's ``Dockerfile``
        and copy its files into the build context."""
        for name, source in self.files.items():
            target = environment_dir / CONTEXT_DIR / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(source, target)
        dockerfile = environment_dir / "Dockerfile"
        dockerfile.write_text(
            f"{dockerfile.read_text().rstrip()}\n\n"
            f"# Added by weval: the Agent, installed once per image.\n"
            f"{self.instructions}\n"
        )


def apt_install(dependencies: tuple[str, ...]) -> str:
    """A RUN instruction that installs Harbor's named system dependencies
    (``ensure_system_dependencies`` names, such as ``"nodejs"``) with
    apt-get, so Harbor later finds their commands and installs nothing."""
    packages = [
        package
        for name in dependencies
        for package in BaseInstalledAgent.SYSTEM_PACKAGES[name].packages["apt-get"]
    ]
    return (
        "RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y "
        f"{shlex.join(packages)} && rm -rf /var/lib/apt/lists/*"
    )


def bash(script: str) -> str:
    """A RUN instruction that runs ``script`` with bash. Harbor's install
    snippets use bash syntax, and Debian's ``/bin/sh`` is dash."""
    return f"RUN {json.dumps(['bash', '-c', script])}"


async def is_preinstalled(
    agent: BaseInstalledAgent, environment: BaseEnvironment
) -> bool:
    """Whether the environment already runs ``agent``'s pinned version, as
    its harness's ``image_layer`` installs it. False when the Agent pins no
    version or Harbor has no version command for it."""
    command = agent.get_version_command()
    if agent.version() is None or command is None:
        return False
    result = await environment.exec(command=command)
    # Pi's parse_version raises on empty output.
    return (
        result.return_code == 0
        and bool(result.stdout)
        and agent.parse_version(result.stdout) == agent.version()
    )
