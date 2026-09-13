import asyncio
import json
from collections import defaultdict
from typing import Any

queues: dict[str, list[asyncio.Queue]] = defaultdict(list)


def subscribe(job_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    queues[job_id].append(queue)
    return queue


def unsubscribe(job_id: str, queue: asyncio.Queue) -> None:
    if queue in queues.get(job_id, []):
        queues[job_id].remove(queue)


def publish(job_id: str, event: dict[str, Any]) -> None:
    payload = json.dumps(event, default=str)
    for queue in list(queues.get(job_id, [])):
        try:
            queue.put_nowait(payload)
        except Exception:
            continue
