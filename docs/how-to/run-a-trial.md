# How to run a Trial

Trials use OpenRouter for the inference, and Modal for any Docker containers.

Run a trial by specifying any env file, task, agent definition, and the number of trials to run (i.e. for higher sample size).

```sh
uv run --env-file .env weval run tasks/<task> --agent <name> [-n 3]
```

Agents are defined and named in `agents.toml`. Use `--agent oracle` to run the Task's own `solution/solve.sh` instead of a model.
