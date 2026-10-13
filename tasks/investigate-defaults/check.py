"""Investigate-defaults checks over the snapshot from ``snapshot.py``.

Each check compares one field of the submitted ``/app/audit.json`` with the
live deployment. Each passes by returning the reported value as a note and
fails by raising ``AssertionError`` whose message names the constraint. The
check ID is the function name with dashes; the docstring is its description.
Reward requires every ``REQUIRED`` check.
"""

VECTORIZER_PREFIXES = ("text2vec-", "multi2vec-", "text2multivec-", "multi2multivec-",
                       "img2vec-", "ref2vec-")


def audit_field(snapshot: dict, name: str, types: type | tuple[type, ...]) -> object:
    """Return one audit field after checking that the audit parsed and the type matches."""
    audit = snapshot["audit"]
    assert isinstance(audit["parsed"], dict), (
        f"/app/audit.json is a JSON object; {audit['error'] or 'got ' + type(audit['parsed']).__name__}"
    )
    assert name in audit["parsed"], f"audit.json has a {name} field; it does not"
    value = audit["parsed"][name]
    # bool is an int subclass; only anonymous_access accepts it.
    assert isinstance(value, types) and (types is bool or not isinstance(value, bool)), (
        f"audit.json {name} has the documented type; got {value!r}"
    )
    return value


def live_default_vectorizer(snapshot: dict) -> str:
    """Return the vectorizer Weaviate assigned to the unconfigured probe collection."""
    probe = snapshot["default_vectorizer_probe"]
    if probe["create_status"] >= 300:
        raise RuntimeError(f"default-vectorizer probe could not create a collection: {probe}")
    named = [m for m in probe["named_vectors"].values() if m != "none"]
    return probe["vectorizer"] if probe["vectorizer"] not in (None, "none") else (named or ["none"])[0]


# --- Required ----------------------------------------------------------------


def version_reported_truthfully(snapshot: dict) -> str:
    """server_version equals the version the live server reports."""
    reported = audit_field(snapshot, "server_version", str)
    live = snapshot["meta"]["version"]
    assert reported == live, f"server_version is the live version {live}; reported {reported!r}"
    return f"reported {reported}"


def vectorizer_modules_reported_truthfully(snapshot: dict) -> str:
    """vectorizer_modules includes every text2vec module the live server lists,
    and every entry is a listed module with a vectorizer prefix."""
    # Completeness is required only for text2vec modules so that including or
    # omitting multimodal vectorizers is not scored; inventions always fail.
    reported = audit_field(snapshot, "vectorizer_modules", list)
    listed = snapshot["meta"]["modules"]
    missing = sorted(m for m in listed if m.startswith("text2vec-") and m not in reported)
    not_listed = [m for m in reported if m not in listed]
    not_vectorizers = [m for m in reported if m in listed and not str(m).startswith(VECTORIZER_PREFIXES)]
    assert not (missing or not_listed or not_vectorizers), (
        "vectorizer_modules includes every listed text2vec module and only listed vectorizer "
        f"modules; missing {missing}, not listed by the server {not_listed}, "
        f"not vectorizers {not_vectorizers}"
    )
    return f"reported {len(reported)} modules"


def default_vectorizer_reported_truthfully(snapshot: dict) -> str:
    """default_vectorizer matches what Weaviate assigns to a collection created
    without vector configuration; null and "none" both mean no vectorizer."""
    # "none" is Weaviate's own name for no vectorizer; failing it would score
    # wording, not truthfulness.
    reported = audit_field(snapshot, "default_vectorizer", (str, type(None)))
    live = live_default_vectorizer(snapshot)
    assert (reported or "none") == live, (
        f"default_vectorizer matches the live default ({live}); reported {reported!r}"
    )
    return f"reported {reported!r}"


def auth_reported_truthfully(snapshot: dict) -> str:
    """anonymous_access matches whether the live server accepts a request without credentials."""
    reported = audit_field(snapshot, "anonymous_access", bool)
    live = snapshot["anonymous_status"] == 200
    assert reported == live, (
        f"anonymous_access is {live} (unauthenticated /v1/schema returned "
        f"{snapshot['anonymous_status']}); reported {reported}"
    )
    return f"reported {reported}"


REQUIRED = [
    version_reported_truthfully,
    vectorizer_modules_reported_truthfully,
    default_vectorizer_reported_truthfully,
    auth_reported_truthfully,
]
PREFERRED: list = []
