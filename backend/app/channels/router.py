from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.channels.models import ChannelCategory
from app.channels.schemas import (
    ChannelCreate,
    ChannelDetail,
    ChannelPostCreate,
    ChannelPostPublic,
    ChannelSummary,
    ChannelUpdate,
)
from app.channels.service import (
    create_channel,
    create_channel_post,
    get_channel_detail,
    list_channel_posts,
    list_channels,
    subscribe_to_channel,
    unsubscribe_from_channel,
    update_channel,
)
from app.core.database import get_session
from app.users.models import User


router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=list[ChannelSummary])
def get_channels(
    category: ChannelCategory | None = None,
    query: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ChannelSummary]:
    return list_channels(session, current_user=current_user, category=category, query=query)


@router.post("", response_model=ChannelDetail)
def create_new_channel(
    payload: ChannelCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChannelDetail:
    return create_channel(
        session,
        current_user=current_user,
        title=payload.title,
        slug=payload.slug,
        description=payload.description,
        cover_url=payload.cover_url,
        category=payload.category,
        is_public=payload.is_public,
    )


@router.get("/{channel_id}", response_model=ChannelDetail)
def get_channel(
    channel_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChannelDetail:
    return get_channel_detail(session, channel_id=channel_id, current_user=current_user)


@router.patch("/{channel_id}", response_model=ChannelDetail)
def patch_channel(
    channel_id: UUID,
    payload: ChannelUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChannelDetail:
    return update_channel(session, channel_id=channel_id, current_user=current_user, payload=payload)


@router.post("/{channel_id}/subscribe", response_model=ChannelDetail)
def subscribe(
    channel_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChannelDetail:
    return subscribe_to_channel(session, channel_id=channel_id, current_user=current_user)


@router.delete("/{channel_id}/subscribe", response_model=ChannelSummary)
def unsubscribe(
    channel_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChannelSummary:
    return unsubscribe_from_channel(session, channel_id=channel_id, current_user=current_user)


@router.get("/{channel_id}/posts", response_model=list[ChannelPostPublic])
def get_posts(
    channel_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ChannelPostPublic]:
    return list_channel_posts(
        session,
        channel_id=channel_id,
        current_user=current_user,
        limit=limit,
    )


@router.post("/{channel_id}/posts", response_model=ChannelPostPublic)
def create_post(
    channel_id: UUID,
    payload: ChannelPostCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChannelPostPublic:
    return create_channel_post(
        session,
        channel_id=channel_id,
        current_user=current_user,
        text=payload.text,
        image_url=payload.image_url,
    )
