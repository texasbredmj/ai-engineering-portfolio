"""Fixed candidates are independent of the benchmark's expected outcomes."""

from .schemas import Call, Decision, Task

CANDIDATES = ("baseline", "wrong-tool", "wrong-arguments", "no-recovery", "false-verifier")


def decide(case_id: str, task: Task, candidate: str) -> Decision:
    if candidate not in CANDIDATES:
        raise ValueError("unknown candidate")
    if task.kind == "sum":
        call = Call(tool="math.sum", arguments={"a": task.a, "b": task.b})
    elif task.kind == "stock":
        call = Call(tool="inventory.read", arguments={"sku": task.sku})
    else:
        call = Call(
            tool="inventory.reserve", arguments={"sku": task.sku, "quantity": task.quantity}
        )
    if candidate == "wrong-tool":
        call = Call(tool="shell.exec", arguments={"command": "untrusted"})
    elif candidate == "wrong-arguments":
        call = call.model_copy(update={"arguments": {"unexpected": 1}})
    return Decision(
        case_id=case_id,
        call=call,
        retry_limit=1 if candidate == "no-recovery" else 3,
        claims_verified=candidate != "false-verifier",
    )
