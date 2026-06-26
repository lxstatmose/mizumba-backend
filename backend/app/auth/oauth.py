import base64
import json
from urllib.parse import urlencode
from urllib.request import urlopen

from app.common.exceptions import unauthorized
from app.core.config import get_settings


def _decode_jwt_payload(id_token: str) -> dict:
    try:
        payload = id_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception as exc:
        raise unauthorized("Invalid OAuth token") from exc


def verify_google_id_token(id_token: str) -> dict:
    settings = get_settings()
    query = urlencode({"id_token": id_token})
    try:
        with urlopen(f"https://oauth2.googleapis.com/tokeninfo?{query}", timeout=5) as response:
            payload = json.loads(response.read())
    except Exception as exc:
        raise unauthorized("Invalid Google token") from exc

    if settings.google_client_id and payload.get("aud") != settings.google_client_id:
        raise unauthorized("Invalid Google token audience")
    if not payload.get("email"):
        raise unauthorized("Google token does not contain email")
    return {
        "email": payload["email"],
        "display_name": payload.get("name") or payload["email"].split("@")[0],
        "avatar_url": payload.get("picture"),
    }


def verify_apple_id_token(id_token: str) -> dict:
    settings = get_settings()
    payload = _decode_jwt_payload(id_token)
    if settings.apple_client_id and payload.get("aud") != settings.apple_client_id:
        raise unauthorized("Invalid Apple token audience")
    if not payload.get("email"):
        raise unauthorized("Apple token does not contain email")
    return {
        "email": payload["email"],
        "display_name": payload.get("name") or payload["email"].split("@")[0],
        "avatar_url": None,
    }
