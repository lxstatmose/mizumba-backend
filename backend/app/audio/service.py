from functools import lru_cache

from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session

from app.audio.schemas import AudioTranscriptionResponse
from app.core.config import get_settings
from app.files.models import FileAssetKind
from app.files.service import save_upload_file
from app.users.models import User


@lru_cache
def _load_whisper_model(model_name: str):
    try:
        import whisper
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Whisper is not installed. Install openai-whisper and ffmpeg to enable transcription.",
        ) from exc

    return whisper.load_model(model_name)


def transcribe_audio_file(
    session: Session,
    *,
    current_user: User,
    upload: UploadFile,
    language: str | None = None,
) -> AudioTranscriptionResponse:
    settings = get_settings()
    if not settings.enable_whisper_transcription:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Whisper transcription is disabled. Set ENABLE_WHISPER_TRANSCRIPTION=true and install optional dependencies.",
        )
    audio_asset = save_upload_file(
        session,
        current_user=current_user,
        upload=upload,
        kind=FileAssetKind.AUDIO,
    )

    model = _load_whisper_model(settings.whisper_model_name)
    result = model.transcribe(
        audio_asset.storage_path,
        language=language or settings.whisper_default_language,
    )

    return AudioTranscriptionResponse(
        text=(result.get("text") or "").strip(),
        language=result.get("language"),
        duration=result.get("duration"),
        file=audio_asset,
    )
