from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlmodel import Session

from app.auth.dependencies import get_user_from_access_token
from app.chats.service import (
    build_chat_summary,
    get_chat_by_id,
    get_chat_member_user_ids,
    get_user_chat_peer_ids,
    mark_chat_read,
    require_chat_member,
)
from app.core.database import engine
from app.messages.service import create_message
from app.notifications.service import get_notifications_for_message
from app.users.models import User
from app.users.service import set_user_online, update_user_last_seen
from app.websocket.broadcaster import publish_to_user, publish_to_users
from app.websocket.events import MessageReadPayload, MessageSendPayload, TypingPayload, WebSocketEvent
from app.websocket.manager import manager


router = APIRouter(tags=["websocket"])


def _event(event_type: str, payload: dict) -> dict:
    return {"type": event_type, "payload": payload}


async def _send_error(websocket: WebSocket, message: str) -> None:
    await websocket.send_json(_event("error", {"message": message}))


async def _broadcast_user_status(
    session: Session,
    *,
    user: User,
    event_type: str,
) -> None:
    peer_ids = get_user_chat_peer_ids(session, user)
    await publish_to_users(
        peer_ids,
        _event(
            event_type,
            {
                "user_id": str(user.id),
                "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
            },
        ),
    )


async def _broadcast_chat_update(session: Session, *, chat_id: UUID) -> None:
    chat = get_chat_by_id(session, chat_id)
    if not chat:
        return

    member_ids = get_chat_member_user_ids(session, chat_id)
    for member_id in member_ids:
        user = session.get(User, member_id)
        if not user:
            continue
        summary = build_chat_summary(session, chat, user)
        await publish_to_user(
            member_id,
            _event("chat.updated", {"chat": summary.model_dump(mode="json")}),
        )


async def _handle_message_send(session: Session, user: User, payload: dict) -> None:
    data = MessageSendPayload.model_validate(payload)
    message = create_message(
        session,
        chat_id=data.chat_id,
        current_user=user,
        text=data.text,
        message_type=data.type,
        attachment_url=data.attachment_url,
        attachment_mime_type=data.attachment_mime_type,
        attachment_name=data.attachment_name,
        attachment_size=data.attachment_size,
        reply_to_id=data.reply_to_id,
    )
    member_ids = get_chat_member_user_ids(session, data.chat_id)
    await publish_to_users(
        member_ids,
        _event("message.created", {"message": message.model_dump(mode="json")}),
    )
    for notification in get_notifications_for_message(session, message.id):
        await publish_to_user(
            notification.user_id,
            _event("notification.created", {"notification": notification.model_dump(mode="json")}),
        )
    await _broadcast_chat_update(session, chat_id=data.chat_id)


async def _handle_message_read(session: Session, user: User, payload: dict) -> None:
    data = MessageReadPayload.model_validate(payload)
    summary = mark_chat_read(
        session,
        chat_id=data.chat_id,
        current_user=user,
        message_id=data.message_id,
    )
    member_ids = get_chat_member_user_ids(session, data.chat_id)
    await publish_to_user(
        user.id,
        _event("chat.updated", {"chat": summary.model_dump(mode="json")}),
    )
    await publish_to_users(
        member_ids,
        _event(
            "message.read",
            {
                "chat_id": str(data.chat_id),
                "user_id": str(user.id),
                "message_id": str(data.message_id) if data.message_id else None,
            },
        ),
    )


async def _handle_typing(session: Session, user: User, payload: dict, event_type: str) -> None:
    data = TypingPayload.model_validate(payload)
    require_chat_member(session, data.chat_id, user)
    member_ids = set(get_chat_member_user_ids(session, data.chat_id))
    member_ids.discard(user.id)
    await publish_to_users(
        member_ids,
        _event(
            event_type,
            {
                "chat_id": str(data.chat_id),
                "user_id": str(user.id),
            },
        ),
    )


async def _handle_event(session: Session, user: User, websocket: WebSocket, raw_event: dict) -> None:
    event = WebSocketEvent.model_validate(raw_event)

    if event.type == "message.send":
        await _handle_message_send(session, user, event.payload)
    elif event.type == "message.read":
        await _handle_message_read(session, user, event.payload)
    elif event.type in {"typing.start", "typing.stop"}:
        await _handle_typing(session, user, event.payload, event.type)
    elif event.type == "ping":
        await websocket.send_json(_event("pong", {}))
    else:
        await _send_error(websocket, f"Unknown event type: {event.type}")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    with Session(engine) as session:
        try:
            user = get_user_from_access_token(session, token)
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        became_online = await manager.connect(user.id, websocket)
        if became_online:
            user = set_user_online(session, user)
            await _broadcast_user_status(session, user=user, event_type="user.online")

        try:
            while True:
                raw_event = await websocket.receive_json()
                try:
                    await _handle_event(session, user, websocket, raw_event)
                except ValidationError as exc:
                    await _send_error(websocket, exc.errors()[0]["msg"])
                except Exception as exc:
                    await _send_error(websocket, str(exc))
        except WebSocketDisconnect:
            pass
        finally:
            became_offline = manager.disconnect(user.id, websocket)
            if became_offline:
                user = update_user_last_seen(session, user)
                await _broadcast_user_status(session, user=user, event_type="user.offline")
