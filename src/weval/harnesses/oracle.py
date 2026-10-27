"""Harbor's built-in Oracle: runs the Task's ``solution/solve.sh``, no model.

Harness protocol members are documented in ``weval.harnesses``.
"""

from harbor.models.trial.config import AgentConfig

EXPECTED_LOGS = ("agent/oracle.txt",)


def agent_config(agent: dict) -> AgentConfig:
    return AgentConfig(name="oracle")


def agent_record(agent: dict) -> dict:
    return dict(agent)
