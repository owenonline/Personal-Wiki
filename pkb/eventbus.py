from __future__ import annotations

import asyncio


class EventBus:
    """Minimal in-process pub/sub for SSE. Subscribers are asyncio.Queues.

    `publish` is sync so it can be called from anywhere — including FastAPI's
    sync (`def`) request handlers, which run in a worker thread, not the event
    loop. Because `asyncio.Queue` is not thread-safe, publish schedules each
    `put_nowait` onto the loop captured at subscribe time via
    `call_soon_threadsafe`, which is the safe cross-thread primitive. Single
    uvicorn process / single event loop assumed.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def subscribe(self) -> asyncio.Queue:
        self._loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict) -> None:
        loop = self._loop
        for q in list(self._subscribers):
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(q.put_nowait, event)
            else:
                q.put_nowait(event)
