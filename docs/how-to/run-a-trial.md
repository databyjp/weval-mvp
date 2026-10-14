# How to run a Trial

Every Trial runs on Modal. Pi Agents use OpenRouter for inference; the Oracle uses no model.

Run a trial by specifying an env file, task, agent definition, and the number of trials to run (e.g. for higher sample size). The env file must define the credentials listed in the [README](../../README.md#setup). The `-n` Trials run concurrently, each in its own Modal sandbox.

```sh
uv run --env-file .env weval run tasks/<task> --agent <name> [-n 3]
```

The run writes `experiment-outputs/<timestamp>-<task>-<agent>/` and prints each Trial's status.

Agents are defined and named in `agents.toml`. Use `--agent oracle` to run the Task's own `solution/solve.sh` instead of a model.
