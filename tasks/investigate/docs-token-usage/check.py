"""investigate/docs-token-usage checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
``deployment``, ``config_ingestion``, and ``search`` answers are not scored;
see the Task page.
``EXPECTED`` gives the value a check looks for, so diagnostics can report
whether the agent was shown it.
"""

import re

ITEMS = (
    "weaviate_version",
    "client_library_versions",
    "deployment",
    "config_ingestion",
    "search",
)


def answer(snapshot: dict, item: str) -> str:
    value = snapshot["findings"]["parsed"][item]["answer"]
    assert isinstance(value, str), (
        f"{item} answer is a string; got {type(value).__name__}"
    )
    return value


def names_version(text: str, version: str) -> bool:
    """Whether ``text`` names ``version`` exactly, so 1.40.1 does not match 1.40.10 or 11.40.1."""
    return re.search(rf"(?<![\d.]){re.escape(version)}(?!\.?\d)", text) is not None


def latest(snapshot: dict, package: str) -> str:
    release = snapshot["latest_releases"][package]
    assert release["version"], (
        f"the latest {package} release was looked up at verify time; {release['error']}"
    )
    return release["version"]


# --- Required ----------------------------------------------------------------


def findings_file(snapshot: dict) -> None:
    """/app/findings.json is a JSON object with every documented item, each
    with an answer string and a sources list."""
    submitted = snapshot["findings"]
    parsed = submitted["parsed"]
    assert isinstance(parsed, dict), (
        f"/app/findings.json is a JSON object; {submitted['error'] or 'got ' + type(parsed).__name__}"
    )
    missing = [item for item in ITEMS if item not in parsed]
    malformed = [
        item
        for item in ITEMS
        if item in parsed
        and not (
            isinstance(parsed[item], dict)
            and isinstance(parsed[item].get("answer"), str)
            and isinstance(parsed[item].get("sources"), list)
            and all(isinstance(url, str) for url in parsed[item]["sources"])
        )
    ]
    assert not (missing or malformed), (
        "findings.json has every item with an answer string and a sources list of URLs; "
        f"missing {missing}, malformed {malformed}"
    )


def weaviate_version_latest(snapshot: dict) -> None:
    """weaviate_version names the latest stable Weaviate release, including its patch."""
    # Trade-off: naming the release passes even if the answer also lists
    # older ones; recommending an older release is not detected.
    version = latest(snapshot, "weaviate")
    assert names_version(answer(snapshot, "weaviate_version"), version), (
        f"weaviate_version names the latest release {version}; got {answer(snapshot, 'weaviate_version')[:200]!r}"
    )


def python_client_version_latest(snapshot: dict) -> None:
    """client_library_versions names the latest weaviate-client (Python)
    release, as its full version or as its minor line (4.24.x)."""
    # The patch is optional because pip resolves it; the Weaviate image tag,
    # by contrast, pins one, so weaviate-version-latest requires it.
    version = latest(snapshot, "weaviate-client")
    minor_line = version.rsplit(".", 1)[0] + ".x"
    text = answer(snapshot, "client_library_versions")
    assert names_version(text, version) or names_version(text, minor_line), (
        f"client_library_versions names the latest Python client release {version} "
        f"or {minor_line}; got {text[:200]!r}"
    )


REQUIRED = [
    findings_file,
    weaviate_version_latest,
    python_client_version_latest,
]
PREFERRED = []
EXPECTED = {
    "weaviate-version-latest": lambda snapshot: snapshot["latest_releases"]["weaviate"][
        "version"
    ],
    "python-client-version-latest": lambda snapshot: snapshot["latest_releases"][
        "weaviate-client"
    ]["version"],
}
