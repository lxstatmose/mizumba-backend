import asyncio
import inspect
import json
from contextlib import suppress
from typing import Any
from uuid import UUID

from app.core.redis import get_redis_client
from app.websocket.manager import manager


WS_REDIS_CHANNEL = "mizumba:websocket:events"

_listener_task: asyncio.Task | None = None


async def publish_to_user(user_id: UUID, event: dict[str, Any]) -> None:
    await publish_to_users({user_id}, event)


async def publish_to_users(user_ids: set[UUID] | list[UUID], event: dict[str, Any]) -> None:
    user_id_values = [str(user_id) for user_id in set(user_ids)]
    if not user_id_values:
        return

    payload = {"user_ids": user_id_values, "event": event}
    try:
        await get_redis_client().publish(WS_REDIS_CHANNEL, json.dumps(payload))
    except Exception:
        # Local fallback keeps development usable when Redis is not running.
        await manager.send_to_users({UUID(user_id) for user_id in user_id_values}, event)


async def _deliver_raw_event(raw_payload: str) -> None:
    payload = json.loads(raw_payload)
    user_ids = {UUID(user_id) for user_id in payload.get("user_ids", [])}
    event = payload.get("event", {})
    await manager.send_to_users(user_ids, event)


async def _close_pubsub(pubsub) -> None:
    close = getattr(pubsub, "aclose", None) or getattr(pubsub, "close", None)
    if close is None:
        return

    result = close()
    if inspect.isawaitable(result):
        await result


async def redis_pubsub_listener() -> None:
    while True:
        pubsub = None
        try:
            pubsub = get_redis_client().pubsub()
            await pubsub.subscribe(WS_REDIS_CHANNEL)

            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                await _deliver_raw_event(message["data"])
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(5)
        finally:
            if pubsub is not None:
                with suppress(Exception):
                    await pubsub.unsubscribe(WS_REDIS_CHANNEL)
                    await _close_pubsub(pubsub)


def start_redis_pubsub_listener() -> asyncio.Task:
    global _listener_task

    if _listener_task is None or _listener_task.done():
        _listener_task = asyncio.create_task(redis_pubsub_listener())
    return _listener_task


async def stop_redis_pubsub_listener() -> None:
    global _listener_task

    if _listener_task is not None:
        _listener_task.cancel()
        with suppress(asyncio.CancelledError):
            await _listener_task
        _listener_task = None
