"""Strict benchmark contracts; external decisions contain data, never executable code."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Task(Strict):
    kind: Literal["sum", "stock", "reserve"]
    a: int = Field(default=0, ge=-10000, le=10000)
    b: int = Field(default=0, ge=-10000, le=10000)
    sku: str = Field(default="demo-kit", pattern=r"^[a-z-]{1,32}$")
    quantity: int = Field(default=1, ge=1, le=10)
    external_content: str = Field(default="", max_length=1024)


class Call(Strict):
    tool: str = Field(min_length=1, max_length=64)
    arguments: dict[str, int | str]

    @model_validator(mode="after")
    def bounded(self):
        if len(self.arguments) > 8:
            raise ValueError("too many arguments")
        if any(
            len(k) > 64 or (isinstance(v, str) and len(v) > 256) for k, v in self.arguments.items()
        ):
            raise ValueError("argument exceeds size budget")
        return self


class Case(Strict):
    id: str = Field(pattern=r"^[a-z0-9-]{1,64}$")
    task: Task
    allowed_tools: list[Literal["math.sum", "inventory.read", "inventory.reserve"]]
    approved: bool = False
    transient_failures: int = Field(default=0, ge=0, le=3)
    expected_call: Call
    expected_status: Literal["SUCCEEDED", "REJECTED", "FAILED"]
    expected_value: int | None
    max_latency_ms: float = Field(default=2000.0, gt=0, le=60000)
    max_tokens: int = Field(default=1000, ge=0, le=100000)
    max_cost_usd: float = Field(default=0.01, ge=0, le=100)


class Decision(Strict):
    case_id: str = Field(pattern=r"^[a-z0-9-]{1,64}$")
    call: Call
    retry_limit: int = Field(default=3, ge=1, le=3)
    input_tokens: int = Field(default=0, ge=0, le=100000)
    output_tokens: int = Field(default=0, ge=0, le=100000)
    model_latency_ms: float = Field(default=0, ge=0, le=60000, allow_inf_nan=False)
    claims_verified: bool = True


class Pricing(Strict):
    input_usd_per_million: float = Field(default=0, ge=0, le=10000, allow_inf_nan=False)
    output_usd_per_million: float = Field(default=0, ge=0, le=10000, allow_inf_nan=False)


def load_jsonl(path: Path, model: type[BaseModel]) -> list:
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("JSONL exceeds 2 MiB budget")
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank record at line {number}")
        records.append(model.model_validate(json.loads(line, object_pairs_hook=unique_keys)))
        if len(records) > 1000:
            raise ValueError("JSONL exceeds 1000 record budget")
    if not records:
        raise ValueError("empty suite")
    ids = [r.id if isinstance(r, Case) else r.case_id for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate record IDs")
    return records


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def canonical_hash(value) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
