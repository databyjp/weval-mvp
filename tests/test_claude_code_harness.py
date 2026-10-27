"""The Claude Code harness downloads each binary once into the host cache,
caches only a binary that matches the release manifest's checksum, and
publishes it once per version to the Modal Volume that Modal Trials mount."""

import gzip
import hashlib
import json
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from weval.harnesses import claude_code
from weval.run import MODAL

BINARY = b"\x7fELF claude code"


def serve(monkeypatch, tmp_path, checksum: str) -> list[str]:
    """Point the cache at ``tmp_path`` and serve a fake release; return the URLs fetched."""
    monkeypatch.setattr(claude_code, "CACHE_DIR", tmp_path)
    manifest = json.dumps({"platforms": {"linux-x64": {"checksum": checksum}}}).encode()
    fetched = []

    def fetch(url: str) -> bytes:
        fetched.append(url)
        return manifest if url.endswith("manifest.json") else BINARY

    monkeypatch.setattr(claude_code, "_fetch", fetch)
    return fetched


def test_binary_is_downloaded_once_and_cached_gzipped(monkeypatch, tmp_path):
    fetched = serve(monkeypatch, tmp_path, hashlib.sha256(BINARY).hexdigest())

    first = claude_code.cached_binary("2.1.292", "linux-x64")
    second = claude_code.cached_binary("2.1.292", "linux-x64")

    assert first == second == tmp_path / "2.1.292/claude-linux-x64.gz"
    assert gzip.decompress(first.read_bytes()) == BINARY
    assert fetched == [
        f"{claude_code.RELEASES}/2.1.292/manifest.json",
        f"{claude_code.RELEASES}/2.1.292/linux-x64/claude",
    ]


def test_concurrent_callers_share_one_download(monkeypatch, tmp_path):
    # Threads hold separate flock opens, as separate processes do.
    fetched = serve(monkeypatch, tmp_path, hashlib.sha256(BINARY).hexdigest())
    fetch = claude_code._fetch
    monkeypatch.setattr(
        claude_code, "_fetch", lambda url: (time.sleep(0.1), fetch(url))[1]
    )

    callers = [
        threading.Thread(
            target=claude_code.cached_binary, args=("2.1.292", "linux-x64")
        )
        for _ in range(4)
    ]
    for caller in callers:
        caller.start()
    for caller in callers:
        caller.join()

    assert len(fetched) == 2


def test_binary_that_fails_the_checksum_is_not_cached(monkeypatch, tmp_path):
    serve(monkeypatch, tmp_path, "0" * 64)

    with pytest.raises(RuntimeError, match="checksum"):
        claude_code.cached_binary("2.1.292", "linux-x64")
    assert not (tmp_path / "2.1.292/claude-linux-x64.gz").exists()


def test_platform_missing_from_the_manifest_is_reported(monkeypatch, tmp_path):
    serve(monkeypatch, tmp_path, hashlib.sha256(BINARY).hexdigest())

    with pytest.raises(ValueError, match="linux-riscv64"):
        claude_code.cached_binary("2.1.292", "linux-riscv64")


class FakeVolume:
    """A Modal Volume holding ``paths``; ``put_file`` records uploads."""

    def __init__(self, paths: list[str]):
        self.paths = paths
        self.uploaded = []

    def listdir(self, path: str):
        entries = [p for p in self.paths if p.startswith(f"{path}/")]
        if not entries:
            raise claude_code.modal.exception.NotFoundError(path)
        return [SimpleNamespace(path=p) for p in entries]

    @contextmanager
    def batch_upload(self):
        yield self

    def put_file(self, local_file, remote_path):
        self.uploaded.append((local_file, remote_path))


def use_volume(monkeypatch, tmp_path, paths: list[str]) -> FakeVolume:
    volume = FakeVolume(paths)
    monkeypatch.setattr(
        claude_code.modal.Volume, "from_name", lambda name, create_if_missing: volume
    )
    monkeypatch.setattr(
        claude_code,
        "cached_binary",
        lambda version, platform: tmp_path / f"{version}-{platform}.gz",
    )
    return volume


def test_volume_gets_each_version_once(monkeypatch, tmp_path):
    volume = use_volume(monkeypatch, tmp_path, ["2.1.292/claude-linux-x64.gz"])

    claude_code.publish_to_volume("2.1.292")
    claude_code.publish_to_volume("2.1.300")

    assert volume.uploaded == [
        (tmp_path / "2.1.300-linux-x64.gz", "/2.1.300/claude-linux-x64.gz")
    ]


def test_modal_environment_mounts_the_volume_read_only(monkeypatch, tmp_path):
    use_volume(monkeypatch, tmp_path, ["2.1.292/claude-linux-x64.gz"])

    environment = claude_code.modal_environment({"version": "2.1.292"}, MODAL)

    assert environment.kwargs == {
        **MODAL.kwargs,
        "volumes": {"/opt/weval/claude-code": "weval-claude-code"},
    }
    assert environment.mounts == [
        {
            "type": "bind",
            "source": "/opt/weval/claude-code",
            "target": "/opt/weval/claude-code",
            "read_only": True,
        }
    ]
