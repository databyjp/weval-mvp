"""The Claude Code harness downloads each binary once into the host cache,
and caches only a binary that matches the release manifest's checksum."""

import gzip
import hashlib
import json

import pytest

from weval.harnesses import claude_code

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


def test_binary_that_fails_the_checksum_is_not_cached(monkeypatch, tmp_path):
    serve(monkeypatch, tmp_path, "0" * 64)

    with pytest.raises(RuntimeError, match="checksum"):
        claude_code.cached_binary("2.1.292", "linux-x64")
    assert not (tmp_path / "2.1.292").exists()


def test_platform_missing_from_the_manifest_is_reported(monkeypatch, tmp_path):
    serve(monkeypatch, tmp_path, hashlib.sha256(BINARY).hexdigest())

    with pytest.raises(ValueError, match="linux-riscv64"):
        claude_code.cached_binary("2.1.292", "linux-riscv64")
