"""Per-run fan-out of asyncio.Queue's (docs/05-BACKEND-SPEC.md §3).

Each subscriber gets its own queue so a slow reader never blocks another.
`close(run_id)` pushes a None sentinel to every subscriber, which the SSE
handler and the demo player both treat as "no more events, end the stream"."""

from __future__ import annotations

import asyncio


class EventBus:
    def __init__(self) -> None:
        self._topics: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._topics.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._topics.get(run_id)
        if subscribers is None:
            return
        if queue in subscribers:
            subscribers.remove(queue)
        if not subscribers:
            self._topics.pop(run_id, None)

    def publish(self, run_id: str, message: dict | None) -> None:
        for queue in self._topics.get(run_id, []):
            queue.put_nowait(message)

    def close(self, run_id: str) -> None:
        self.publish(run_id, None)
        self._topics.pop(run_id, None)


# -- process-wide singleton -------------------------------------------------

_bus = EventBus()


def get_bus() -> EventBus:
    return _bus
