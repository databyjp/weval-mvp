# Glossary

These definitions are authoritative for `weval`. Add a term only when the project uses it to distinguish concepts that would otherwise be ambiguous.

**Experiment.** A plan comprising one or more Trials; for running one Task under one or more Conditions for a fixed number of repetitions.

**Experiment run.** One execution of an Experiment.

**Evaluation.** Defining Tasks, running Experiments, and interpreting the resulting agent behavior.

**Task.** An agent challenge defined by question, prompt, evaluation criteria, and provided infrastructure.

**Agent harness.** The program through which a model acts in the Task environment, including its version, tools, skills, and extensions.

**Model configuration.** The provider-specific model selection and credential reference used by an Agent harness.

**Condition.** One pairing of an Agent harness and a Model configuration under which a Task is attempted.

**Trial.** One attempt to complete a Task under one Condition.

**Non-result.** A Trial for which evaluation infrastructure prevented a valid Task outcome from being observed. A Non-result records the cause.
