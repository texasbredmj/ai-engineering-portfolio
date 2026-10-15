"""Isolated mock backend with policy enforcement and receipts, no external effects."""

from pydantic import Field, ValidationError

from .schemas import Call, Case, Strict


class SumArgs(Strict):
    a: int = Field(ge=-10000, le=10000)
    b: int = Field(ge=-10000, le=10000)


class ReadArgs(Strict):
    sku: str = Field(pattern=r"^[a-z-]{1,32}$")


class ReserveArgs(ReadArgs):
    quantity: int = Field(ge=1, le=10)


SCHEMAS = {"math.sum": SumArgs, "inventory.read": ReadArgs, "inventory.reserve": ReserveArgs}


class MockBackend:
    def __init__(self, case: Case):
        self.case = case
        self.stock = {"demo-kit": 10, "spare-kit": 4}
        self.receipts = []
        self.attempts = 0

    def invoke(self, call: Call) -> tuple[str, int | None]:
        self.attempts += 1
        unauthorized = (
            call.tool not in self.case.allowed_tools
            or call.tool not in SCHEMAS
            or (call.tool == "inventory.reserve" and not self.case.approved)
        )
        if unauthorized:
            self.receipts.append(
                {
                    "attempt": self.attempts,
                    "status": "REJECTED",
                    "unauthorized": True,
                    "effect": False,
                }
            )
            return "REJECTED", None
        try:
            args = SCHEMAS[call.tool].model_validate(call.arguments)
        except ValidationError:
            self.receipts.append(
                {
                    "attempt": self.attempts,
                    "status": "INVALID_ARGUMENTS",
                    "unauthorized": False,
                    "effect": False,
                }
            )
            raise
        if self.attempts <= self.case.transient_failures:
            self.receipts.append(
                {
                    "attempt": self.attempts,
                    "status": "TRANSIENT",
                    "unauthorized": False,
                    "effect": False,
                }
            )
            return "TRANSIENT", None
        value = None
        status = "SUCCEEDED"
        if isinstance(args, SumArgs):
            value = args.a + args.b
        elif args.sku not in self.stock:
            status = "FAILED"
        elif isinstance(args, ReserveArgs):
            if self.stock[args.sku] < args.quantity:
                status = "FAILED"
            else:
                self.stock[args.sku] -= args.quantity
                value = self.stock[args.sku]
        else:
            value = self.stock[args.sku]
        self.receipts.append(
            {
                "attempt": self.attempts,
                "status": status,
                "unauthorized": False,
                "effect": call.tool == "inventory.reserve" and status == "SUCCEEDED",
                "value": value,
            }
        )
        return status, value
