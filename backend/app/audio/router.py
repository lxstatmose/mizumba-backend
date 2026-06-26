from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlmodel import Session

from app.audio.schemas import AudioTranscriptionResponse
from app.audio.service import transcribe_audio_file
from app.auth.dependencies import get_current_user
from app.core.database import get_session
from app.users.models import User


router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("/transcribe", response_model=AudioTranscriptionResponse)
def transcribe_audio(
    upload: UploadFile = File(...),
    language: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AudioTranscriptionResponse:
    return transcribe_audio_file(
        session,
        current_user=current_user,
        upload=upload,
        language=language,
    )
