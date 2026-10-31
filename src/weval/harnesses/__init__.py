"""Harness adapters: one module per agent harness, dispatched through
``run.HARNESSES``.

Every harness module provides:

- ``agent_config(agent) -> AgentConfig``: Harbor's agent configuration for one
  ``agents.toml`` entry.
- ``agent_record(agent) -> dict``: the Agent as recorded in ``weval.json``.
- ``EXPECTED_LOGS``: Trial-relative log paths the harness must leave behind;
  a missing one makes the Trial's status ``incomplete``.

And may provide:

- ``image_layer(agent) -> preinstall.ImageLayer``: the Agent's installation
  as Dockerfile instructions, appended to the Task image for ``--local``
  runs. The harness's ``install`` must skip what the layer installed and fall
  back to a full install without it (``preinstall.is_preinstalled``).
- ``modal_environment(agent, environment) -> EnvironmentConfig``: Modal-only
  environment setup, such as mounting a Volume; not called for ``--local``
  runs.
- ``token_usage(trial_dir) -> dict``: usage fields that replace Harbor's
  ``result.json`` figures when the harness records better ones.
- ``model_error(trial_dir) -> str | None``: the provider's error message when
  the agent's session ended because its last model request failed (after the
  harness's own retries), else ``None``. Such a Trial is a ``non-result``.
"""
