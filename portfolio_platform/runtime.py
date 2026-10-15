"""Runtime factories, authenticated ledger bridge, and integrated Temporal activities."""
import json
import os
import time
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from temporalio import activity
from temporalio.exceptions import ApplicationError

from workflow_orchestrator import activities as original
from workflow_orchestrator.ledger import Ledger
from tool_gateway.app import create_app as gateway_app, from_environment
from tool_gateway.models import ReservationInput


def tool_app():
    config = from_environment()
    config.rate_per_minute = 10000
    return gateway_app(config)


def bridge_app():
    ledger = Ledger()
    ledger.initialize()
    with ledger.connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS platform_requests(workflow_id text PRIMARY KEY, request jsonb NOT NULL)")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get('/health')
    def health():
        with ledger.connect() as db:
            db.execute('SELECT 1 FROM inventory LIMIT 1')
        return {'ready': True}

    def auth(authorization: str = Header(default="")):
        import secrets
        if not secrets.compare_digest(authorization, "Bearer " + os.environ['GATEWAY_UPSTREAM_TOKEN']):
            raise HTTPException(401, 'bridge credential required')

    def result(workflow_id):
        evidence = ledger.evidence(workflow_id)
        row = evidence['reservation']
        if not row:
            raise HTTPException(404, 'reservation not found')
        with ledger.connect() as db:
            stored = db.execute('SELECT request FROM platform_requests WHERE workflow_id=%s', (workflow_id,)).fetchone()
        return {'workflow_id': workflow_id, 'quantity': stored['request']['quantity'],
                'state': row['state'], 'observed_quantity': row['quantity']}

    @app.post('/reservations', dependencies=[Depends(auth)])
    def reserve(body: ReservationInput):
        with ledger.connect() as db:
            stored = db.execute('SELECT request FROM platform_requests WHERE workflow_id=%s', (body.workflow_id,)).fetchone()
        if not stored or stored['request']['quantity'] != body.quantity:
            raise HTTPException(403, 'matching normalized workflow request required')
        try:
            ledger.reserve(body.workflow_id, stored['request'])
        except ValueError:
            raise HTTPException(403, 'matching durable workflow approval required') from None
        # Deliberate, bounded fault fixture. One transaction corrupts quantity and stock together.
        if stored['request']['fail_verification']:
            with ledger.connect() as db:
                row = db.execute('SELECT * FROM reservations WHERE workflow_id=%s FOR UPDATE', (body.workflow_id,)).fetchone()
                if row['quantity'] == body.quantity:
                    db.execute('UPDATE reservations SET quantity=quantity+1 WHERE workflow_id=%s', (body.workflow_id,))
                    db.execute('UPDATE inventory SET stock=stock-1 WHERE sku=%s', (row['sku'],))
        return result(body.workflow_id)

    @app.get('/reservations/{workflow_id}', dependencies=[Depends(auth)])
    def inspect(workflow_id: str):
        return result(workflow_id)

    return app


def tool_request(path, body, admin=False):
    token = os.environ['GATEWAY_ADMIN_TOKEN' if admin else 'GATEWAY_OPERATOR_TOKEN']
    with httpx.Client(base_url=os.environ['TOOL_GATEWAY_URL'], timeout=12, trust_env=False) as client:
        response = client.post(path, json=body, headers={'Authorization': 'Bearer ' + token})
        response.raise_for_status()
        return response.json()


@activity.defn(name='inspect_inventory')
def inspect_inventory(request: dict) -> dict:
    workflow_id = activity.info().workflow_id
    gateway = tool_request('/v1/tools/file.metadata/invoke',
                           {'arguments': {'path': 'pyproject.toml'}, 'idempotency_key': workflow_id + '-inspect'})
    if not gateway['verified_completion']:
        raise ApplicationError('tool gateway inspection not verified', non_retryable=True)
    return {**original.inspect_inventory(request), 'gateway': gateway}


@activity.defn(name='quote_order')
def quote_order(request: dict) -> dict:
    quote = original.quote_order(request)
    with httpx.Client(timeout=8, trust_env=False) as client:
        response = client.post(os.environ['MODEL_GATEWAY_URL'] + '/v1/generate',
            headers={'Authorization': 'Bearer ' + os.environ['GATEWAY_API_KEY'],
                     'Idempotency-Key': activity.info().workflow_id + '-model'},
            json={'model': 'alpha-pro', 'prompt': 'Explain the approved inventory reservation fixture.',
                  'mode': 'text', 'max_output_tokens': 32, 'max_cost_nusd': 1000000})
        response.raise_for_status()
        model = response.json()
    return {**quote, 'model_gateway': model, 'paid_model_calls': 0}


@activity.defn(name='reserve_inventory')
def reserve_inventory(data: dict) -> dict:
    from psycopg.types.json import Jsonb
    workflow_id, request = data['workflow_id'], data['request']
    with Ledger().connect() as db:
        db.execute('INSERT INTO platform_requests VALUES(%s,%s) ON CONFLICT DO NOTHING', (workflow_id, Jsonb(request)))
        existing = db.execute('SELECT request FROM platform_requests WHERE workflow_id=%s', (workflow_id,)).fetchone()
        if existing['request'] != request:
            raise ApplicationError('workflow request conflict', non_retryable=True)
    args = {'workflow_id': workflow_id, 'quantity': request['quantity']}
    approval = tool_request('/v1/approvals', {'tool_id': 'inventory.reserve', 'arguments': args})
    tool_request('/v1/approvals/' + approval['approval_id'] + '/decision', {'approve': True}, admin=True)
    report = tool_request('/v1/tools/inventory.reserve/invoke', {'arguments': args,
        'idempotency_key': workflow_id + '-reserve', 'approval_id': approval['approval_id']})
    # The workflow independently verifies the ledger even when the gateway detects a mismatch.
    if report['state'] not in ('SUCCEEDED', 'UNVERIFIED'):
        raise ApplicationError('tool gateway reservation failed', non_retryable=True)
    if request['pause_after_commit'] and activity.info().attempt == 1:
        # Existing Project 03 crash fixture: deliberately withhold the activity acknowledgement.
        while True:
            activity.heartbeat('gateway reservation committed; awaiting worker restart')
            time.sleep(.2)
    return {**Ledger().evidence(workflow_id)['reservation'], 'gateway': report,
            'attempt': activity.info().attempt}


ACTIVITIES = [a for a in original.ACTIVITIES if a.__name__ not in {'inspect_inventory','quote_order','reserve_inventory'}]
ACTIVITIES += [inspect_inventory, quote_order, reserve_inventory]
