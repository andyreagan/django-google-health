from googlehealth import constants


def test_all_scopes_use_googlehealth_prefix():
    scope_names = [
        name
        for name in dir(constants)
        if name.startswith("SCOPE_") and name != "SCOPE_PREFIX"
    ]
    for name in scope_names:
        value = getattr(constants, name)
        assert value.startswith(constants.SCOPE_PREFIX), name


def test_api_endpoint_is_versioned():
    assert constants.API_BASE_URL == "https://health.googleapis.com"
    assert constants.API_VERSION == "v4"
