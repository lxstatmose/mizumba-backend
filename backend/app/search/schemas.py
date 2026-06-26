from uuid import UUID

from pydantic import BaseModel


class SearchItem(BaseModel):
    id: UUID
    type: str
    title: str
    subtitle: str | None = None
    url: str | None = None


class SearchResponse(BaseModel):
    users: list[SearchItem]
    chats: list[SearchItem]
    messages: list[SearchItem]
    channels: list[SearchItem]
