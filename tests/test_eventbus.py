import asyncio

import pytest

from pkb.eventbus import EventBus


@pytest.mark.asyncio
async def test_subscriber_receives_published_event():
    bus = EventBus()
    q = await bus.subscribe()
    bus.publish({"type": "home_changed"})
    event = await asyncio.wait_for(q.get(), timeout=1)
    assert event["type"] == "home_changed"


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    bus = EventBus()
    q = await bus.subscribe()
    bus.unsubscribe(q)
    bus.publish({"type": "x"})
    assert q.empty()


@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive():
    bus = EventBus()
    q1 = await bus.subscribe()
    q2 = await bus.subscribe()
    bus.publish({"type": "ping"})
    assert (await asyncio.wait_for(q1.get(), 1))["type"] == "ping"
    assert (await asyncio.wait_for(q2.get(), 1))["type"] == "ping"
