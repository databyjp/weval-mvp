"""Harbor's built-in Oracle: runs the Task's ``solution/solve.sh``, no model."""

from harbor.models.trial.config import AgentConfig

EXPECTED_LOGS = ("agent/oracle.txt",)


def agent_config(condition: dict) -> AgentConfig:
    return AgentConfig(name="oracle")


def condition_record(condition: dict) -> dict:
    return dict(condition)
