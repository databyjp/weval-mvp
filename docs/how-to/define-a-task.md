# How to define a Task

Each task is defined as a unique directory under `tasks/<stage>/<scenario>/`. The stage is `build`, `deploy`, `resolve`, or `investigate`; [`AGENTS.md`](../../AGENTS.md#task-definition) defines each.

A task consists of `instruction.md` (the prompt), `environment/` (what the agent is provided), `task.toml` (task meta-parameters such as timeouts, used directly by Harbor), `snapshot.py` (what to capture from the live stack after the agent finishes), `check.py` (what to check for scoring), and `solution/solve.sh` (the Oracle solution).

See the [reference](../reference.md) for details on each parameter.

## Task page

Each Task states its motivation in one of two places, and `tests/test_task_pages.py` enforces whichever it uses.

A page at `docs/tasks/<stage>/<scenario>.md`, shaped like [resolve/sku-search](../tasks/resolve/sku-search.md), must have:

- a `motivation` in its YAML frontmatter;
- a checks table whose rows, such as ``| `check-id` | REQUIRED | ... |``, list exactly the checks and tiers in `check.py`.

Alternatively, `task.toml` sets `[metadata] motivation`, as `build/ecommerce-search` does. Every check function then needs a docstring, and the Task must have no page.

## Oracle and calibration

Each task must have an Oracle solution that passes every check.

It also needs "calibrations": known-to-fail variations on the Oracle snapshot. They live in a test module under `tests/`, not in the Task directory. See `tests/test_deploy_local_instance_check.py` for an example.

To write the calibrations:

1. Run the Oracle (`--agent oracle`) and copy the Trial's `verifier/snapshot.json` under `tests/fixtures/`, as in `deploy-local-instance-oracle-snapshot.json`.
2. For each check, write a function that changes the snapshot the way a plausible wrong solution would, such as a legacy vectorizer or a missing object.
3. Assert that the Oracle snapshot passes every check, and that each broken variant fails only its targeted check, for the stated reason.

## Expected values

When a check looks for one value that the snapshot holds, such as the latest release, `check.py` can name it in `EXPECTED`, a mapping from check ID to a function of the snapshot:

```python
EXPECTED = {
    "python-client-version-latest": lambda snapshot: snapshot["latest_releases"][
        "weaviate-client"
    ]["version"],
}
```

`weval check` then reports, under each failed check, whether the agent was shown that exact value in a tool result. "Not seen" means the agent's sources never gave the answer; "seen" means it had the answer and wrote something else. `EXPECTED` doesn't affect scoring, and a check without an entry gets no such line. See `tasks/investigate/current-practices/check.py`.
