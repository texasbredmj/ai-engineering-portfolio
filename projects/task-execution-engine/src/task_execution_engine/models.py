from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Operation = Literal["inspect", "format_fix", "format_check", "lint", "test"]
OPERATION_ORDER = ["inspect", "format_fix", "format_check", "lint", "test"]


class State(StrEnum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    PLANNED = "PLANNED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TRANSITIONS = {
    State.CREATED: {State.VALIDATED, State.FAILED, State.CANCELLED},
    State.VALIDATED: {State.PLANNED, State.FAILED, State.CANCELLED},
    State.PLANNED: {State.AUTHORIZED, State.WAITING_APPROVAL, State.FAILED, State.CANCELLED},
    State.WAITING_APPROVAL: {State.AUTHORIZED, State.FAILED, State.CANCELLED},
    State.AUTHORIZED: {State.RUNNING, State.FAILED, State.CANCELLED},
    State.RUNNING: {State.RETRYING, State.VERIFYING, State.FAILED, State.CANCELLED},
    State.RETRYING: {State.RUNNING, State.FAILED, State.CANCELLED},
    State.VERIFYING: {State.SUCCEEDED, State.FAILED, State.CANCELLED},
    State.SUCCEEDED: set(),
    State.FAILED: set(),
    State.CANCELLED: set(),
}


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    repository: str = Field(min_length=1)
    operations: list[Operation] = Field(min_length=1, max_length=5)
    authorized_operations: list[Operation]
    idempotency_key: str = Field(min_length=1, max_length=128, pattern=r"^[\w.-]+$")
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_attempts: int = Field(default=1, ge=1, le=3)
    execution_budget_seconds: float = Field(default=120.0, gt=0, le=900)

    @model_validator(mode="after")
    def unique_operations(self):
        if len(set(self.operations)) != len(self.operations):
            raise ValueError("operations must be unique")
        if self.operations != sorted(self.operations, key=OPERATION_ORDER.index):
            raise ValueError("operations must follow inspect, format_fix, format_check, lint, test")
        if {"test", "format_fix"}.intersection(self.operations) and self.max_attempts != 1:
            raise ValueError("test and format_fix are not retryable; use max_attempts=1")
        if "format_fix" in self.operations and not {"format_check", "lint", "test"}.issubset(
            self.operations
        ):
            raise ValueError("format_fix requires subsequent format_check, lint, and test")
        return self

    def canonical(self):
        data = self.model_dump()
        data["repository"] = str(Path(self.repository).resolve())
        return data


class Result(BaseModel):
    operation: str
    attempt: int
    argv: list[str]
    started_at: str
    finished_at: str
    duration_seconds: float
    exit_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    output_truncated: bool = False
    error: str | None = None
