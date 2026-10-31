# How to run a Trial

Trials run on Modal unless you pass `--local`. Pi Agents use OpenRouter for inference. Claude Code Agents use OpenRouter or, with `auth = "subscription"`, a Claude subscription. The Oracle uses no model.

Run a trial by specifying an env file, task, agent definition, and the number of trials to run (1 by default; pass `-n` for a higher sample size). The env file must define the credentials listed in the [README](../../README.md#setup). The `-n` Trials run concurrently, each in its own Modal sandbox.

```sh
uv run --env-file .env weval run tasks/<stage>/<scenario> --agent <name> [-n 3] [--local] [--treatment <treatment>] [--draft]
```

`--local` runs the Trials on the local Docker daemon instead, at no Modal cost. Any Agent can run a Task whose `task.toml` sets [`[metadata] docker = false`](../reference.md#tasktoml) locally, such as `investigate/docs-token-usage`: its agent gets no Docker socket. On a Task that uses Docker, the agent's container would hold the host's Docker socket, which is root on the host and reaches the credentials in `.env`, so `weval run` refuses a local run of any Agent but the Oracle unless you also pass `--unsafe-local`. Modal is the isolation boundary for those runs.

`--treatment` gives the Agent a [Treatment](../reference.md#treatments)'s skills, its prompt for the Task, or both, named after a directory in `treatments/`. Run the baseline the same way without it, with the same Agent.

`--draft` runs a Task whose `task.toml` marks it a [draft](../reference.md#tasktoml); without it, `weval run` refuses the Task before anything runs.

Each `weval run` is one Experiment run. It writes `experiment-outputs/<timestamp>__<stage>__<scenario>__<agent>/`, with `<agent>+<treatment>` in place of `<agent>` for a Treatment, and prints each Trial's status.

Agents are defined and named in `agents.toml`. Use `--agent oracle` to run the Task's own `solution/solve.sh` instead of a model.
