from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.common.exceptions import not_found
from app.core.database import get_session
from app.users.models import User
from app.users.schemas import UserProfile, UserPublic, UserUpdate
from app.users.service import get_profile_stats, get_user_by_id, update_user_profile


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    return update_user_profile(session, current_user, payload)


@router.get("/me/profile", response_model=UserProfile)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> UserProfile:
    return UserProfile(user=current_user, stats=get_profile_stats(session, current_user))


@router.get("/{user_id}/profile", response_model=UserProfile)
def get_user_profile(user_id: UUID, session: Session = Depends(get_session)) -> UserProfile:
    user = get_user_by_id(session, user_id)
    if not user or not user.is_active:
        raise not_found("User not found")
    return UserProfile(user=user, stats=get_profile_stats(session, user))
