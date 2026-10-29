# Weval

`Weval` is an "agent experience" (AX) evaluation harness for Weaviate. It runs Weaviate-related Tasks against agent harnesses and scores each Trial against its predefined Checks.

Domain terms (e.g. Task, Agent, Trial, Non-result) are defined in [`GLOSSARY.md`](../GLOSSARY.md).

## Tech stack

`weval` is built on top of Harbor, a coding-agent testing framework. This allows us to focus on Weaviate-specific implementation details, and outsource important, but already-implemented details such as container and agent orchestration.

- Modal is used for runs requiring Docker-based Weaviate instances for convenience and parallelisation.
- OpenRouter is generally used for providing API-based model access. Subscriptions (e.g. Claude Code or Codex) may be used where available.

## Key Concepts

Each "Task" is defined in `tasks/<stage>/<scenario>`.

A Task comprises Harbor definition (`task.toml`) and an instruction (`instruction.md`), to be carried out by an agent in the environment defined by the Task's `environment/` directory. Each run's outputs are captured through `snapshot.py`, and reviewed through criteria in `check.py`

The outputs from a task are captured in `experiment-outputs`, under `<YYYYMMDD>-<HHMMSS>__<stage>__<scenario>__<agent>`, with `<agent>+<treatment>` for a Treatment run. `weval report` renders the retained runs as a static site at `experiment-outputs/index.html`; its "How weval works" page diagrams each step.

A "Trial" is an attempt at a Task. Thus it requires an agent definition. An "Experiment" defines a plan comprising one or more Trials. An Experiment may also include "Treatments", which give the agent extra skills, a replacement prompt, or both.

[Task runs](concepts/task-runs.md) describes how a run moves between `weval`, Harbor, and the verifier.

## Docs

These docs follow the diataxis framework.
- [Task runs](concepts/task-runs.md)
- [How to define a Task](how-to/define-a-task.md)
- [How to run a Trial](how-to/run-a-trial.md)
- [How to read a Trial](how-to/read-a-trial.md)
- [Reference](reference.md): `task.toml`, verifier flags, and the Trial directory
- Tasks: one directory each under [`tasks/`](../tasks/), named `<stage>/<scenario>`.
