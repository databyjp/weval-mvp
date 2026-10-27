"""investigate/db-recommendation checks over the snapshot from ``snapshot.py``.

Each check passes by returning and fails by raising ``AssertionError`` whose
message names the constraint. The check ID is the function name with dashes;
the docstring is its description. Reward requires every ``REQUIRED`` check.
A Trial of a prompt variant is also scored on that prompt variant's
``PROMPT_VARIANT_REQUIRED`` and ``PROMPT_VARIANT_PREFERRED`` lists;
``default`` is ``instruction.md``, the others are
``prompts/<prompt-variant>.md``.
Reading which stores the recommendation names is deferred; see the Task page.
"""


# --- Required ----------------------------------------------------------------


def recommendation_file(snapshot: dict) -> None:
    """/app/RECOMMENDATION.md exists and is not blank."""
    submitted = snapshot["recommendation"]
    assert submitted["text"] is not None, (
        f"/app/RECOMMENDATION.md exists; {submitted['error']}"
    )
    assert submitted["text"].strip(), (
        "/app/RECOMMENDATION.md is not blank; it holds only whitespace"
    )


REQUIRED = [recommendation_file]
PREFERRED: list = []
# Placeholders: every prompt variant is scored on the shared checks.
PROMPT_VARIANT_REQUIRED: dict[str, list] = {
    "default": [],
    "vector-database": [],
}
PROMPT_VARIANT_PREFERRED: dict[str, list] = {
    "default": [],
    "vector-database": [],
}
