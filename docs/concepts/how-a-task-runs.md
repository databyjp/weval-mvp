# How a Trial runs

A Trial consists of two processes. `weval` runs on the host device. It packages the Task, starts Harbor, and records the result. `verify.py` runs inside the Trial environment, which may be Modal for local Docker-based runs.

`weval run` triggers `weval.run.run()`. Each run looks as follows:

- Weval "packages" a Task, with instructions, the verifier infrastructure (verify.py), task-specific checks (check.py) and the Test run file (test.sh)
- Weval creates a Harbor job config, and runs it asynchronously.
- Harbor takes the created `JobConfig` and runs the trial.
- Verification occurs based on the defined "checks" for the Task.
