from app.geo.service import get_auth_provider_options


def test_auth_provider_options_hide_google_and_apple_for_ru() -> None:
    options = get_auth_provider_options("RU")

    assert options["google"] is False
    assert options["apple"] is False


def test_auth_provider_options_use_default_for_unknown_country() -> None:
    options = get_auth_provider_options("US")

    assert options["google"] is True
    assert options["apple"] is True
