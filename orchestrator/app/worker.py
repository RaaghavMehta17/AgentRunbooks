from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker
from prometheus_client import start_http_server

from .settings import Settings
from .workflows import RunbookWorkflow
from . import activities


async def main() -> None:
    settings = Settings()
    start_http_server(9100)
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue="runbook-queue",
        workflows=[RunbookWorkflow],
        activities=[
            activities.load_context,
            activities.policy_validate,
            activities.wait_for_approval,
            activities.plan_step,
            activities.invoke_adapter,
            activities.record_step,
            activities.compensate,
            activities.compute_shadow,
            activities.update_run_totals,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

