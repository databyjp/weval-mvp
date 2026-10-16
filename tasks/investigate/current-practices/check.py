"""investigate/current-practices checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
Criteria for the answers are deferred; see the Task page.
"""

ITEMS = ("weaviate_version", "python_client_version", "deployment",
         "vectorization", "indexing", "search")


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
        item for item in ITEMS
        if item in parsed and not (
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


REQUIRED = [findings_file]
PREFERRED: list = []
