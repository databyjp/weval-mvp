"""investigate/client-code-examples checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
Prose answers are not scored; see the Task page.
"""

import re

ITEMS = ("deployment", "config_ingestion", "search")
CODE_ITEMS = ("config_ingestion", "search")
LANGUAGES = ("python", "typescript", "go")

# Current vector configuration APIs. Python 4.16 replaced
# vectorizer_config=Configure.Vectorizer; TypeScript 3.8 replaced
# configure.vectorizer with configure.vectors, which the docs import as
# ``vectors``. Neither pattern matches the legacy spelling.
PYTHON_VECTOR_CONFIG = re.compile(r"Configure\.Vectors\.|\bvector_config\s*=")
TYPESCRIPT_VECTOR_CONFIG = re.compile(r"\bvectors\.\w+\(")
# Go v6 is a collections-first redesign. The docs show v5 and v6 tabs side by
# side, so v5 calls next to v6 ones mean the agent mixed the two clients.
GO_V6 = re.compile(r"\.Collections\.\w+\(|weaviate-go-client/v6")
GO_V5 = re.compile(
    r"\.Schema\(\)|\.GraphQL\(\)|\.Batch\(\)\.ObjectsBatcher\(|weaviate-go-client/v[45]\b"
)
HYBRID = {
    "python": re.compile(r"\.query\.hybrid\("),
    "typescript": re.compile(r"\.query\.hybrid\("),
    "go": re.compile(r"\.Query\.Hybrid\("),
}


def code(snapshot: dict, item: str, language: str) -> str:
    value = snapshot["findings"]["parsed"][item]["code"][language]
    assert isinstance(value, str), (
        f"{item} {language} code is a string; got {type(value).__name__}"
    )
    return value


def well_formed(entry: object, item: str) -> bool:
    if not (
        isinstance(entry, dict)
        and isinstance(entry.get("answer"), str)
        and isinstance(entry.get("sources"), list)
        and all(isinstance(url, str) for url in entry["sources"])
    ):
        return False
    if item not in CODE_ITEMS:
        return True
    snippets = entry.get("code")
    return isinstance(snippets, dict) and all(
        isinstance(snippets.get(language), str) for language in LANGUAGES
    )


# --- Required ----------------------------------------------------------------


def findings_file(snapshot: dict) -> None:
    """/app/findings.json is a JSON object with every documented item, each
    with an answer string and a sources list, and Python, TypeScript, and Go
    code strings for config_ingestion and search."""
    submitted = snapshot["findings"]
    parsed = submitted["parsed"]
    assert isinstance(parsed, dict), (
        f"/app/findings.json is a JSON object; {submitted['error'] or 'got ' + type(parsed).__name__}"
    )
    missing = [item for item in ITEMS if item not in parsed]
    malformed = [
        item for item in ITEMS if item in parsed and not well_formed(parsed[item], item)
    ]
    assert not (missing or malformed), (
        "findings.json has every item with an answer, sources, and code where documented; "
        f"missing {missing}, malformed {malformed}"
    )


def python_current_vector_config(snapshot: dict) -> None:
    """config_ingestion's Python code uses the current vector configuration
    API (vector_config=Configure.Vectors), not the legacy
    vectorizer_config=Configure.Vectorizer."""
    # Detection: the prompt asks for code, not for an API.
    text = code(snapshot, "config_ingestion", "python")
    assert PYTHON_VECTOR_CONFIG.search(text), (
        f"config_ingestion Python code uses vector_config=Configure.Vectors; got {text[:200]!r}"
    )


def typescript_current_vector_config(snapshot: dict) -> None:
    """config_ingestion's TypeScript code uses the current vector configuration
    API (configure.vectors, imported as vectors), not the legacy
    configure.vectorizer."""
    text = code(snapshot, "config_ingestion", "typescript")
    assert TYPESCRIPT_VECTOR_CONFIG.search(text), (
        f"config_ingestion TypeScript code uses vectors.<module>(); got {text[:200]!r}"
    )


def go_v6_client(snapshot: dict) -> None:
    """config_ingestion's and search's Go code use the v6 client's collections
    API and no v5 calls (Schema(), GraphQL(), Batch().ObjectsBatcher())."""
    wrong = {}
    for item in CODE_ITEMS:
        text = code(snapshot, item, "go")
        if v5 := GO_V5.search(text):
            wrong[item] = f"v5 call {v5.group(0)}"
        elif not GO_V6.search(text):
            wrong[item] = f"no v6 collections API in {text[:120]!r}"
    assert not wrong, (
        f"Go code uses the v6 collections API and no v5 calls; got {wrong!r}"
    )


REQUIRED = [
    findings_file,
    python_current_vector_config,
    typescript_current_vector_config,
    go_v6_client,
]


# --- Preferred ---------------------------------------------------------------


def hybrid_search_code(snapshot: dict) -> None:
    """search's code runs a hybrid query in every language."""
    # Detection: the docs recommend hybrid search as the starting point, and
    # the prompt asks only for the recommended way to search.
    missing = [
        language
        for language in LANGUAGES
        if not HYBRID[language].search(code(snapshot, "search", language))
    ]
    assert not missing, (
        f"search code runs a hybrid query in every language; not in {missing}"
    )


PREFERRED = [hybrid_search_code]
