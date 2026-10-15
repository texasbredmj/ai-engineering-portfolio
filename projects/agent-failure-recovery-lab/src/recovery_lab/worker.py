"""Bounded durable worker, request replay protected by backend idempotency."""

import json
import random
import time
import urllib.error
from pathlib import Path

from pydantic import ValidationError

from .contracts import Receipt, Request, call, local_url
from .store import LEGAL, Store, exclusive


def verify(data, request):
    receipt = Receipt.model_validate(data)
    return receipt.task_id == request.task_id and receipt.quantity == request.quantity


def execute(request: Request, db: Path, url: str, timeout=1.0):
    url = local_url(url)
    if not 0.05 <= timeout <= 10:
        raise ValueError("request timeout must be between 0.05 and 10 seconds")
    with exclusive(db):
        store = Store(db)
        started = time.monotonic()
        cpu_start = time.process_time()
        rng = random.Random(request.task_id)
        try:
            store.create(request)
            task = store.task(request.task_id)
            if task["report"]:
                return json.loads(task["report"])
            state = task["state"]
            if state in {"RUNNING", "VERIFYING"}:
                store.transition(request.task_id, "RETRYING")
                store.event(request.task_id, "resumed", {"attempts": task["attempts"]})
            for state in ["VALIDATED", "PLANNED", "AUTHORIZED"]:
                if state in LEGAL[store.task(request.task_id)["state"]]:
                    store.transition(request.task_id, state)
            verified = False
            permanent = False
            confirmed_absent = False
            while store.task(request.task_id)["attempts"] < 3:
                store.transition(request.task_id, "RUNNING")
                store.attempt(request.task_id)
                retry_after = None
                try:
                    data = call(url, "/execute", request.model_dump(), timeout=timeout)
                    if not verify(data, request):
                        raise ValueError("receipt mismatch")
                except urllib.error.HTTPError as exc:
                    error = f"http_{exc.code}"
                    permanent = exc.code not in {429, 500, 502, 503, 504}
                    if exc.code == 429:
                        try:
                            retry_after = max(
                                0, min(0.2, float(exc.headers.get("Retry-After", "0")))
                            )
                        except ValueError:
                            retry_after = 0.05
                    store.event(request.task_id, "error", {"classification": error})
                except (ValueError, ValidationError):
                    store.event(request.task_id, "error", {"classification": "malformed_response"})
                except (OSError, urllib.error.URLError, TimeoutError):
                    store.event(request.task_id, "error", {"classification": "transport"})
                # Query the receipt independently even after a plausible success response.
                store.transition(request.task_id, "VERIFYING")
                try:
                    evidence = call(url, "/receipt/" + request.task_id, timeout=2.0)
                    confirmed_absent = evidence["receipt"] is None
                    if evidence["receipt"] and verify(evidence["receipt"], request):
                        verified = True
                        break
                except (OSError, ValueError, KeyError, urllib.error.URLError, ValidationError):
                    store.event(request.task_id, "verification_unavailable", {})
                if permanent:
                    break
                store.transition(request.task_id, "RETRYING")
                attempt = store.task(request.task_id)["attempts"]
                delay = max(
                    retry_after or 0, min(0.2, 0.04 * 2 ** (attempt - 1)) + rng.uniform(0, 0.01)
                )
                store.event(request.task_id, "backoff", {"seconds": delay})
                time.sleep(delay)
            ambiguous = any(
                e["kind"] == "verification_unavailable"
                or (
                    e["kind"] == "error"
                    and json.loads(e["detail"])["classification"]
                    in {"transport", "malformed_response"}
                )
                for e in store.history(request.task_id)
            )
            state = (
                "SUCCEEDED"
                if verified
                else ("FAILED" if confirmed_absent and not ambiguous else "HUMAN_REQUIRED")
            )
            # Lack of a receipt after ambiguous transport errors cannot prove no effect.
            # Explicit dependency failures can be checked by the independent harness.
            report = {
                "task_id": request.task_id,
                "state": state,
                "verified": verified,
                "attempts": store.task(request.task_id)["attempts"],
                "duration_seconds": time.monotonic() - started,
                "cpu_seconds": time.process_time() - cpu_start,
            }
            return store.finish(request.task_id, state, report)
        finally:
            store.close()
