# How to define a Task

Each task is defined as a unique directory under `tasks/<name>/`.

A task consists of `instruction.md` (the prompt), `environment/` (what the agent is provided),`task.toml` (task meta-parameters such as timeouts, used directly by Harbor), `snapshot.py` (what to capture from the task), `check.py` (what to check for scoring), and `solution/solve.sh` (the Oracle solution).

See the reference documentation for detailed on each parameter.

## Oracle & Calibration

Each task must have an Oracle solution that passes every check.

It must also include a set of "calibrations" which are known-to-fail variations on the Oracle solution.

To generate the calibrations, run the Oracle solution, save its snapshot under `tests/fixtures/`, and write one test per calibration-table row confirming each broken variant fails only its targeted check (`AGENTS.md`, "Calibration").
