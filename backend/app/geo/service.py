from fastapi import Request

from app.core.config import get_settings


COUNTRY_HEADERS = (
    "CF-IPCountry",
    "X-Country-Code",
    "X-App-Country",
)


def get_country_code_from_request(request: Request) -> str:
    settings = get_settings()

    for header in COUNTRY_HEADERS:
        value = request.headers.get(header)
        if value:
            return value.upper()

    return settings.default_country_code.upper()


def get_auth_provider_options(country_code: str) -> dict[str, bool]:
    settings = get_settings()
    country_code = country_code.upper()
    rules = settings.auth_provider_rules
    default_options = rules.get("DEFAULT", {"google": True, "apple": True})
    return rules.get(country_code, default_options)
