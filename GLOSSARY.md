# Glossary

## General

These definitions are authoritative for `weval`. Add a term only when the project uses it to distinguish concepts that would otherwise be ambiguous.

**Experiment.** A plan comprising one or more Trials; for running one Task by one or more Agents, with or without Treatments, for a fixed number of repetitions.

**Experiment run.** One execution of an Experiment.

**Evaluation.** Defining Tasks, running Experiments, and interpreting the resulting agent behavior.

**Task.** An agent challenge defined by question, prompt, evaluation criteria, and provided infrastructure.

**Agent harness.** The program through which a model acts in the Task environment, including its version and the tools and extensions installed for every run of it.

**Model configuration.** The provider-specific model selection and credential reference used by an Agent harness.

**Agent.** One Agent harness plus one Model configuration, named in `agents.toml`.

**Treatment.** Skills, a replacement prompt, MCP servers, documentation, or other additions given to an Agent to answer an experimental question. A Trial without a Treatment is a baseline.

**Trial.** One attempt to complete a Task by one Agent, with or without a Treatment.

**Non-result.** A Trial for which evaluation infrastructure prevented a valid Task outcome from being observed. A Non-result records the cause.

**Timed-out.** A Trial in which the Agent hit a Harbor limit, such as the time budget, but the verifier still scored the submission. The reward is recorded; a Timed-out Trial does not count as passed.

## Weaviate

**Schema.** A collection's property names and data types.

**Collection definition.** A collection's full configuration: its schema, property tokenization, vectorizer, vector index, and module settings. Snapshots store it under the key `schema`, after Weaviate's `/v1/schema` endpoint.
