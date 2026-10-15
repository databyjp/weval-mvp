# Weval

We are building `weval` to assess and improve Weaviate's "agent experience". It runs Weaviate coding Tasks against agent harnesses and scores each Trial against the Task's checks.

Domain terms (e.g. Task, Agent, Trial, Non-result) are defined in [`GLOSSARY.md`](../GLOSSARY.md).

## Tech stack

`weval` is built on top of Harbor, a coding-agent testing framework. This allows us to focus on Weaviate-specific implementation details, and outsource important, but already-solved details such as container and agent orchestration.

For convenient orchestration of Docker-in-Docker and Trial parallelisation, `weval` uses Modal for Docker-based runs.

## Architecture

Think of `weval` as a set of Weaviate-related "Tasks" that agents are to perform, which will be then evaluated by `weval`.

A "Trial" is an attempt at a Task, and thus it requires an agent definition. An "Experiment" defines a plan comprising one or more Trials. An Experiment may also include "Treatments", such as additional agent skills, MCPs or other tools to be given to the agent.

[Task runs](concepts/task-runs.md) describes how a run moves between `weval`, Harbor, and the verifier.

## Docs

These docs follow the diataxis framework.
- [Task runs](concepts/task-runs.md)
- [How to define a Task](how-to/define-a-task.md)
- [How to run a Trial](how-to/run-a-trial.md)
- [How to read a Trial](how-to/read-a-trial.md)
- [Reference](reference.md): `task.toml`, verifier flags, and the Trial directory
- Tasks: [resolve/sku-search](tasks/resolve/sku-search.md)
