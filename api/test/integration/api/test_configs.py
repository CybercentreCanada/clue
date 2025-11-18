def test_get_config(login_session):
    session, host = login_session
    data = session.get(f"{host}/api/v1/configs").json()

    assert set(data["api_response"].keys()) == {"configuration", "c12nDef"}


def test_get_config_origins(login_session):
    session, host = login_session
    data = session.get(f"{host}/api/v1/configs").json()

    assert "cors_origins" in data["api_response"]["configuration"]["ui"]


def test_get_schema(login_session):
    session, host = login_session
    data = session.get(f"{host}/api/v1/configs/schema/plugin_response").json()

    assert set(data["api_response"].keys()) == {"$defs", "properties", "title", "type", "required"}
    assert data["api_response"]["title"] == "QueryResult"


def test_get_schema_fail(login_session):
    session, host = login_session
    result = session.get(f"{host}/api/v1/configs/schema/doesntexist")

    assert not result.ok
