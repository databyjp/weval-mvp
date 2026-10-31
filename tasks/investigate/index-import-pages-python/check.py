"""investigate/index-import-pages-python checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
Neither the recommendations nor the code are scored: the Task measures
the tokens spent reading a fixed set of pages. See the Task page.
"""

ITEMS = ("vector_index", "compression", "batch_import")
CODE_ITEMS = ("vector_index", "batch_import")
LANGUAGES = ("python",)


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
    with an answer string and a sources list, and a Python code string for
    vector_index and batch_import."""
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


REQUIRED = [findings_file]
PREFERRED = []
