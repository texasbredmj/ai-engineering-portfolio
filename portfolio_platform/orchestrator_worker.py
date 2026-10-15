import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from temporalio.client import Client
from temporalio.worker import Worker
from workflow_orchestrator.ledger import Ledger
from workflow_orchestrator.workflow import FulfillmentWorkflow
from portfolio_platform.runtime import ACTIVITIES


async def main():
    Ledger().initialize()
    client = await Client.connect(os.environ['TEMPORAL_ADDRESS'])
    with ThreadPoolExecutor(max_workers=8) as executor:
        await Worker(client, task_queue='portfolio-integrated-v1', workflows=[FulfillmentWorkflow],
                     activities=ACTIVITIES, activity_executor=executor).run()


if __name__ == '__main__':
    asyncio.run(main())

