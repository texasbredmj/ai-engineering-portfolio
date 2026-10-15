"""Durable dashboard-to-Temporal dispatcher. The external ledger is authoritative."""
import asyncio
import os
import time
import uuid
from datetime import timedelta

from psycopg.types.json import Jsonb
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from ops_center.config import Settings
from ops_center.store import Store
from ops_center.worker import Worker as DashboardWorker
from workflow_orchestrator.ledger import Ledger
from workflow_orchestrator.policy import Order, sign_decision
from workflow_orchestrator.workflow import FulfillmentWorkflow
from portfolio_platform.metrics import call_metrics


class Dispatcher:
    def __init__(self, store, client):
        self.store, self.client = store, client
        self.worker = DashboardWorker(store, 'temporal-dispatcher', lease_seconds=30)
        with store.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS platform_runs(
                task_id uuid NOT NULL REFERENCES tasks(id), attempt integer NOT NULL,
                workflow_id text UNIQUE NOT NULL, state text NOT NULL DEFAULT 'ACTIVE',
                PRIMARY KEY(task_id,attempt))''')

    def bind(self, task):
        with self.store.connect() as db:
            db.execute('SELECT id FROM tasks WHERE id=%s FOR UPDATE', (task['id'],))
            run = db.execute("SELECT * FROM platform_runs WHERE task_id=%s AND state='ACTIVE' ORDER BY attempt DESC LIMIT 1", (task['id'],)).fetchone()
            if not run:
                run = db.execute('INSERT INTO platform_runs(task_id,attempt,workflow_id) VALUES(%s,%s,%s) RETURNING *',
                    (task['id'], task['attempts'], f"ops-{task['id']}-{task['attempts']}")).fetchone()
            return run

    def finish(self, task, run, report):
        outputs = report.get('outputs', {})
        verification = outputs.get('verification', {})
        observed = verification.get('reservation')
        verified = report.get('verified_completion') is True and verification.get('verified') is True
        state = 'SUCCEEDED' if verified else 'FAILED'
        retryable = not verified and task['mode'] == 'transient' and task['attempts'] < task['max_attempts']
        with self.store.connect() as db:
            current = db.execute('SELECT * FROM tasks WHERE id=%s FOR UPDATE', (task['id'],)).fetchone()
            active = db.execute('SELECT state FROM platform_runs WHERE workflow_id=%s FOR UPDATE', (run['workflow_id'],)).fetchone()
            if active['state'] != 'ACTIVE':
                return
            if current['state'] != 'RUNNING' or current['claim'] != task['claim']:
                # A cancellation owns terminal state; Temporal compensation/report remains inspectable.
                if current['state'] == 'CANCELLED':
                    self.store.event(db, task['id'], 'ORCHESTRATOR_CANCELLED', self.worker.id, report)
                    db.execute("UPDATE platform_runs SET state='CANCELLED' WHERE workflow_id=%s", (run['workflow_id'],))
                return
            receipt = uuid.uuid5(uuid.NAMESPACE_URL, run['workflow_id'])
            if observed:
                db.execute('INSERT INTO effects(task_id,quantity,receipt) VALUES(%s,%s,%s) ON CONFLICT(task_id) DO NOTHING',
                           (task['id'], observed['quantity'], receipt))
            details = {'expected_quantity': task['quantity'],
                'observed_quantity': observed['quantity'] if observed else None,
                'receipt': str(receipt) if observed else None,
                'method': 'Project 03 independent PostgreSQL inventory verification',
                'claimed_completed': bool(outputs.get('reservation')),
                'workflow_id': run['workflow_id'], 'orchestrator_report': report,
                'mirror_only': 'Dashboard effect row is a projection; Project 03 inventory ledger is authoritative'}
            if observed:
                db.execute('INSERT INTO evidence(task_id,verified,details) VALUES(%s,%s,%s) ON CONFLICT(task_id) DO UPDATE SET verified=excluded.verified,details=excluded.details,at=now()',
                           (task['id'], verified, Jsonb(details)))
            for item in report.get('history', []):
                self.store.event(db, task['id'], 'ORCHESTRATOR_' + item['state'], self.worker.id,
                                 {'workflow_id': run['workflow_id'], 'workflow_time': item['at']})
            db.execute('INSERT INTO spans(span_id,task_id,trace_id,parent_span_id,name,duration_ms,attributes) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                       (uuid.uuid4().hex[:16], task['id'], task['trace_id'], task['id'].hex[:16],
                        'task.verify', 0, Jsonb({'workflow_id': run['workflow_id'], 'verification.passed': verified,
                                              'duration_scope': 'verification result projection; timing not measured here'})))
            calls = [('file.metadata', outputs.get('inspect', {}).get('gateway')),
                     ('model.generate', outputs.get('quote', {}).get('model_gateway')),
                     ('inventory.reserve', outputs.get('reservation', {}).get('gateway'))]
            for name, result in calls:
                if result:
                    metrics=call_metrics(name,result)
                    db.execute('INSERT INTO tool_calls(task_id,attempt,tool,state,duration_ms,input_tokens,output_tokens,cost_nusd,details) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                        (task['id'], task['attempts'], name, result.get('state', 'SUCCEEDED'),
                         metrics['duration_ms'],metrics['input_tokens'],metrics['output_tokens'],metrics['cost_nusd'],Jsonb(result)))
                    db.execute('INSERT INTO spans(span_id,task_id,trace_id,name,duration_ms,attributes) VALUES(%s,%s,%s,%s,%s,%s)',
                        (uuid.uuid4().hex[:16], task['id'], task['trace_id'], 'platform.' + name,
                         metrics['duration_ms'], Jsonb({'workflow_id': run['workflow_id'], 'source': name, 'duration_scope': 'gateway-reported; zero when not supplied'})))
            self.store.event(db, task['id'], state, self.worker.id, {'verified': verified, 'retryable': retryable, 'workflow_id': run['workflow_id']})
            error = None if verified else 'orchestrator failed; inspect independent verification and workflow history'
            db.execute('UPDATE tasks SET state=%s,retryable=%s,error=%s,version=version+1,claim=NULL,lease_until=NULL,updated_at=now() WHERE id=%s',
                       (state, retryable, error, task['id']))
            db.execute('UPDATE platform_runs SET state=%s WHERE workflow_id=%s', (state, run['workflow_id']))
            db.execute('UPDATE agents SET processed=processed+1 WHERE id=%s', (self.worker.id,))

    async def execute(self, task):
        run = self.bind(task)
        failures = 3 if task['mode'] == 'permanent' or (task['mode'] == 'transient' and run['attempt'] == 1) else 0
        request = Order(requester='dashboard-requester', quantity=task['quantity'],
                        pause_after_commit=task['mode']=='restart',
                        approval_timeout_seconds=300, fail_verification=task['mode'] == 'unverified',
                        transient_quote_failures=failures).model_dump()
        try:
            handle = await self.client.start_workflow(FulfillmentWorkflow.run, request,
                id=run['workflow_id'], task_queue='portfolio-integrated-v1',
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
                execution_timeout=timedelta(minutes=5))
        except WorkflowAlreadyStartedError:
            handle = self.client.get_workflow_handle(run['workflow_id'])
        signalled = False
        while True:
            self.worker.heartbeat()
            with self.store.connect() as db:
                current = db.execute('SELECT state,claim FROM tasks WHERE id=%s', (task['id'],)).fetchone()
                db.execute("UPDATE tasks SET lease_until=now()+interval '30 seconds' WHERE id=%s AND claim=%s AND state='RUNNING'", (task['id'], task['claim']))
            if current['state'] == 'CANCELLED':
                await handle.cancel()
            elif current['claim'] != task['claim']:
                return
            status = await handle.query(FulfillmentWorkflow.status)
            if status['state'] == 'WAITING_APPROVAL' and not signalled:
                # Approval tasks reach this worker only after backend-authorized human approval.
                await handle.signal(FulfillmentWorkflow.decision,
                    sign_decision(run['workflow_id'], status['request'], os.environ['ORCHESTRATOR_APPROVAL_KEY']))
                signalled = True
            if status['state'] in {'SUCCEEDED','FAILED','CANCELLED'}:
                report = Ledger().report(run['workflow_id'])
                if report:
                    self.finish(task, run, report)
                    return
            await asyncio.sleep(0.4)


async def main():
    store = Store(Settings())
    store.initialize()
    client = await Client.connect(os.environ['TEMPORAL_ADDRESS'])
    dispatcher = Dispatcher(store, client)
    while True:
        dispatcher.worker.heartbeat()
        task = dispatcher.worker.claim()
        if task:
            try:
                await dispatcher.execute(task)
            except Exception as error:
                # Leave the durable workflow mapping active. The lease permits safe reattachment.
                print('dispatcher retry after ' + type(error).__name__, flush=True)
                await asyncio.sleep(2)
        await asyncio.sleep(0.3)


if __name__ == '__main__':
    asyncio.run(main())
