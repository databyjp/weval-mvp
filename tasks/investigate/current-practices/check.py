"""investigate/current-practices checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
A Trial of a prompt variant is also scored on that prompt variant's
``PROMPT_VARIANT_REQUIRED`` and ``PROMPT_VARIANT_PREFERRED`` lists;
``default`` is ``instruction.md``, the others are
``prompts/<prompt-variant>.md``.
``deployment`` and ``search`` answers are not scored; see the Task page.
``EXPECTED`` gives the value a check looks for, so diagnostics can report
whether the agent was shown it.
"""

import re
from urllib.parse import urlparse

ITEMS = (
    "weaviate_version",
    "client_library_versions",
    "deployment",
    "config_ingestion",
    "search",
)
# Current Python client API for vectorizer configuration (client 4.16 and
# later); the legacy one is vectorizer_config=Configure.Vectorizer.
CURRENT_VECTOR_CONFIG = re.compile(
    r"Configure\.Vectors\b|\bvector_config\b|named vectors?", re.IGNORECASE
)
# Weaviate-owned sites, and the package registries of the official clients,
# including the API hosts agents query for versions (registry.npmjs.org,
# repo1.maven.org, proxy.golang.org).
CANONICAL_HOSTS = (
    "weaviate.io",
    "pypi.org",
    "npmjs.com",
    "npmjs.org",
    "pkg.go.dev",
    "proxy.golang.org",
    "nuget.org",
    "central.sonatype.com",
    "maven.org",
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


def is_canonical(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").removeprefix("www.")
    if host == "github.com":
        return parsed.path.lower().startswith("/weaviate/")
    if host == "api.github.com":
        return parsed.path.lower().startswith("/repos/weaviate/")
    return any(host == h or host.endswith("." + h) for h in CANONICAL_HOSTS)


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
    """client_library_versions names the latest weaviate-client (Python) release, including its patch."""
    version = latest(snapshot, "weaviate-client")
    text = answer(snapshot, "client_library_versions")
    assert names_version(text, version), (
        f"client_library_versions names the latest Python client release {version}; got {text[:200]!r}"
    )


def current_vector_config(snapshot: dict) -> None:
    """config_ingestion recommends the current vector configuration API
    (vector_config=Configure.Vectors, named vectors), not the legacy
    vectorizer_config=Configure.Vectorizer."""
    # Detection: the prompt does not ask for an API. Mentioning the legacy API
    # as replaced is allowed, so only the current one's presence is checked.
    text = answer(snapshot, "config_ingestion")
    assert CURRENT_VECTOR_CONFIG.search(text), (
        f"config_ingestion names vector_config, Configure.Vectors, or named vectors; got {text[:200]!r}"
    )


# --- Preferred ---------------------------------------------------------------


def canonical_sources(snapshot: dict) -> None:
    """Every answer cites at least one source, and every source is a Weaviate
    site (weaviate.io, github.com/weaviate) or an official client's package registry."""
    parsed = snapshot["findings"]["parsed"]
    # Items missing from the file are findings-file's failure, not this check's.
    present = [item for item in ITEMS if item in parsed]
    uncited = [item for item in present if not parsed[item]["sources"]]
    other = sorted(
        {
            url
            for item in present
            for url in parsed[item]["sources"]
            if not is_canonical(url)
        }
    )
    assert not (uncited or other), (
        f"every answer cites canonical sources; uncited {uncited}, non-canonical {other}"
    )


REQUIRED = [
    findings_file,
    weaviate_version_latest,
    python_client_version_latest,
    current_vector_config,
]
PREFERRED = [canonical_sources]
EXPECTED = {
    "weaviate-version-latest": lambda snapshot: snapshot["latest_releases"]["weaviate"][
        "version"
    ],
    "python-client-version-latest": lambda snapshot: snapshot["latest_releases"][
        "weaviate-client"
    ]["version"],
}
# Placeholders for checks that differ by use case.
PROMPT_VARIANT_REQUIRED: dict[str, list] = {
    "default": [],
    "help-chatbot": [],
    "shopping-search": [],
    "legal-archive": [],
}
PROMPT_VARIANT_PREFERRED: dict[str, list] = {
    "default": [],
    "help-chatbot": [],
    "shopping-search": [],
    "legal-archive": [],
}
