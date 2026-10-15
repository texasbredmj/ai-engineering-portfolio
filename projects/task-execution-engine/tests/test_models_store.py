from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from task_execution_engine.models import Request, State
from task_execution_engine.store import Store


def request(root, **overrides):
    return Request(
        repository=str(root),
        operations=["inspect"],
        authorized_operations=["inspect"],
        idempotency_key="unit",
        **overrides,
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"operations": ["shell"]},
        {"timeout_seconds": 0},
        {"max_attempts": 4},
        {"operations": []},
        {"operations": ["inspect", "inspect"]},
        {"operations": ["test"], "max_attempts": 2},
        {"command": "echo unsafe"},
    ],
)
def test_request_rejects_unsafe_inputs(tmp_path, overrides):
    data = request(tmp_path).model_dump()
    data.update(overrides)
    with pytest.raises(ValidationError):
        Request.model_validate(data)


def test_state_transitions_and_persistence(tmp_path):
    store = Store(tmp_path / "data")
    task_id, _ = store.create(request(tmp_path))
    with pytest.raises(ValueError, match="illegal transition"):
        store.transition(task_id, State.SUCCEEDED)
    store.transition(task_id, State.VALIDATED)
    reopened = Store(tmp_path / "data")
    assert reopened.get(task_id)["state"] == "VALIDATED"
    assert [e["event"] for e in reopened.get(task_id)["audit"]] == ["created", "transition"]


def test_concurrent_idempotency_and_conflict(tmp_path):
    store = Store(tmp_path / "data")
    req = request(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.create(req), range(8)))
    assert len({task_id for task_id, _ in results}) == 1
    assert sum(created for _, created in results) == 1
    changed = req.model_copy(update={"timeout_seconds": 12.0})
    with pytest.raises(ValueError, match="different request"):
        store.create(changed)


def test_unknown_task(tmp_path):
    with pytest.raises(KeyError):
        Store(tmp_path).get("unknown")
