# How to run a Trial

Trials run on Modal unless you pass `--local`. Pi Agents use OpenRouter for inference; the Oracle uses no model.

Run a trial by specifying an env file, task, agent definition, and the number of trials to run (1 by default; pass `-n` for a higher sample size). The env file must define the credentials listed in the [README](../../README.md#setup). The `-n` Trials run concurrently, each in its own Modal sandbox.

```sh
uv run --env-file .env weval run tasks/<stage>/<scenario> --agent <name> [-n 3] [--local] [--prompt-variant <prompt-variant>] [--treatment <treatment>] [--draft]
```

`--local` runs the Trials on the local Docker daemon instead, at no Modal cost. Use it for Tasks that don't need Docker-in-Docker, such as `investigate/current-practices`.

`--prompt-variant` runs one of the Task's [prompt variants](../reference.md#prompt-variants), named after a file in its `prompts/` directory without `.md`.

`--treatment` gives the Agent a [Treatment](../reference.md#treatments)'s skills, named after a directory in `treatments/`. Run the baseline the same way without it, with the same Agent and prompt variant.

`--draft` runs a Task whose `task.toml` marks it a [draft](../reference.md#tasktoml); without it, `weval run` refuses the Task before anything runs.

Each `weval run` is one Experiment run. It writes `experiment-outputs/<timestamp>__<stage>__<scenario>__<agent>/`, with `<scenario>@<prompt-variant>` in place of `<scenario>` for a prompt variant and `<agent>+<treatment>` in place of `<agent>` for a Treatment, and prints each Trial's status.

Agents are defined and named in `agents.toml`. Use `--agent oracle` to run the Task's own `solution/solve.sh` instead of a model.
