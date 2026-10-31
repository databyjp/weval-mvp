"""An Agent installed into the Trial image (``image_layer``) is not
installed again at setup, and setup falls back to the full install when the
image lacks the pinned version."""

import asyncio
from types import SimpleNamespace

import pytest
from harbor.agents.installed.opencode import OpenCode
from harbor.agents.installed.pi import Pi

from weval.harnesses.opencode import PreinstalledOpenCode
from weval.harnesses.pi import WEB_ACCESS_VERSION, WebAccessPi

MODEL = "openrouter/z-ai/glm-5.3"


class FakeImage:
    """A Trial container holding ``installed`` tools ("opencode", "pi",
    "pi-web-access") at the given versions. It answers each tool's version
    check from them, and ``npm ci`` installs the pinned extension. Every
    other command succeeds. Records commands and upload targets."""

    default_user = None

    def __init__(self, **installed: str | None):
        self.installed = installed
        self.commands: list[str] = []
        self.uploads: list[str] = []

    async def exec(self, command, **_):
        self.commands.append(command)
        if "npm ci" in command:
            self.installed["pi-web-access"] = WEB_ACCESS_VERSION
        for tool in ("opencode", "pi"):
            if f"{tool} --version" in command:
                version = self.installed.get(tool)
                return result(0, f"{version}\n") if version else result(127)
        # The extension check exits 1 unless the pinned version is installed.
        if "node -e" in command:
            pinned = self.installed.get("pi-web-access") == WEB_ACCESS_VERSION
            return result(0 if pinned else 1)
        return result(0)

    async def upload_file(self, source, target):
        self.uploads.append(target)


def result(return_code: int, stdout: str = ""):
    return SimpleNamespace(return_code=return_code, stdout=stdout, stderr="")


@pytest.fixture
def harbor_installs(monkeypatch):
    """Harbor's own installs, replaced by a record of the agents they ran for."""
    calls = []

    async def install(agent, environment):
        calls.append(type(agent).__name__)

    monkeypatch.setattr(OpenCode, "install", install)
    monkeypatch.setattr(Pi, "install", install)
    return calls


@pytest.mark.parametrize(
    ("in_image", "installs"),
    [("1.19.4", False), ("1.19.3", True), (None, True)],
    ids=["pinned", "other-version", "absent"],
)
def test_opencode_installs_unless_the_image_has_the_pinned_version(
    tmp_path, harbor_installs, in_image, installs
):
    agent = PreinstalledOpenCode(logs_dir=tmp_path, version="1.19.4", model_name=MODEL)

    asyncio.run(agent.install(FakeImage(opencode=in_image)))

    assert harbor_installs == (["PreinstalledOpenCode"] if installs else [])


@pytest.mark.parametrize(
    ("in_image", "installs"),
    [("0.85.1", False), ("0.85.0", True), (None, True)],
    ids=["pinned", "other-version", "absent"],
)
def test_pi_installs_unless_the_image_has_the_pinned_version(
    tmp_path, harbor_installs, in_image, installs
):
    agent = WebAccessPi(logs_dir=tmp_path, version="0.85.1", model_name=MODEL)
    image = FakeImage(pi=in_image, **{"pi-web-access": WEB_ACCESS_VERSION})

    asyncio.run(agent.install(image))

    assert harbor_installs == (["WebAccessPi"] if installs else [])


@pytest.mark.parametrize(
    ("in_image", "installs"),
    [(WEB_ACCESS_VERSION, False), ("0.0.1", True), (None, True)],
    ids=["pinned", "other-version", "absent"],
)
def test_web_access_installs_unless_the_image_has_the_pinned_version(
    tmp_path, harbor_installs, in_image, installs
):
    agent = WebAccessPi(logs_dir=tmp_path, version="0.85.1", model_name=MODEL)
    image = FakeImage(pi="0.85.1", **{"pi-web-access": in_image})

    asyncio.run(agent.install(image))

    assert any("npm ci" in c for c in image.commands) == installs
    # Setup ends by checking the pinned version, which raises on a mismatch.
    assert "node -e" in image.commands[-1]


def test_pi_from_the_image_still_gets_its_config_and_logs(tmp_path, harbor_installs):
    agent = WebAccessPi(logs_dir=tmp_path, version="0.85.1", model_name=MODEL)
    image = FakeImage(pi="0.85.1", **{"pi-web-access": WEB_ACCESS_VERSION})

    asyncio.run(agent.install(image))

    assert set(image.uploads) >= {
        "/tmp/harbor-pi-agent/web-search.json",
        "/logs/agent/pi-web-access-package-lock.json",
        "/logs/agent/web-search.json",
        "/logs/agent/web-access.json",
    }
