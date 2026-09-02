from flask.testing import FlaskClient


def test_index_returns_success_message(client: FlaskClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert b"InfraManager est\xc3\xa1 funcionando." in response.data


def test_health_returns_ok(client: FlaskClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
