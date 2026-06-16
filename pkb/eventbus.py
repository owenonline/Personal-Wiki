from __future__ import annotations

import asyncio


class EventBus:
    """Minimal in-process pub/sub. Subscribers are asyncio.Queues; publish is
    sync (callable from request handlers) and fans out via put_nowait. Single
    uvicorn process / single event loop assumed."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict) -> None:
        for q in list(self._subscribers):
            q.put_nowait(event)
