"""A connection failure during investigate/current-practices' release fetches
is recorded in the snapshot instead of raising, so the agent's submitted
findings survive and the Trial is not reduced to the error sentinel."""

import urllib.error

from conftest import ROOT, load_module

SNAPSHOT_FILE = ROOT / "tasks/investigate/current-practices/snapshot.py"


def test_snapshot_records_a_connection_failure_instead_of_raising(monkeypatch):
    module = load_module(SNAPSHOT_FILE)

    def refuse(url, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    snapshot = module.snapshot(None)

    assert "findings" in snapshot
    for release in snapshot["latest_releases"].values():
        assert release["version"] is None
        assert release["status"] is None
        assert "connection refused" in release["error"]


def test_rate_limited_api_falls_back_to_the_releases_feed(monkeypatch):
    module = load_module(SNAPSHOT_FILE)
    # Shape of the 403 retained Trials recorded, and of the feed's entry links.
    feed = "".join(
        f'<link rel="alternate" type="text/html" href="https://github.com/weaviate/weaviate/releases/tag/{tag}"/>'
        for tag in ("v1.39.13", "v1.40.1", "v1.41.0-rc.1", "v1.40.0")
    )
    responses = {
        module.SERVER_RELEASES: (
            403,
            {"message": "API rate limit exceeded for 18.193.102.150."},
        ),
        module.SERVER_RELEASES_FEED: (200, feed),
    }
    monkeypatch.setattr(module, "request", lambda url: responses[url])

    release = module.latest_server_release()

    assert release["version"] == "1.40.1"
    assert release["source"] == module.SERVER_RELEASES_FEED
