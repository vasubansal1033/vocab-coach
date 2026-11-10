from fastapi.testclient import TestClient


def test_healthz_is_public(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_base_page_has_attribution_link(client: TestClient, make_user, login_as) -> None:
    login_as(make_user("Ada"))
    response = client.get("/")
    assert response.status_code == 200
    # SPA shell when frontend/dist exists; otherwise Jinja home.
    if 'id="root"' in response.text:
        assert "vocab-coach" in response.text
        me = client.get("/api/me", headers={"accept": "application/json"})
        assert me.status_code == 200
        assert me.json()["display_name"] == "Ada"
    else:
        assert 'href="/about/attribution"' in response.text
        assert "Ada" in response.text
    assert client.get("/about/attribution").status_code == 200


def test_static_app_css_is_served(client: TestClient) -> None:
    assert client.get("/static/app.css").status_code == 200


def test_empty_session_secret_is_refused() -> None:
    import pytest

    from vocab.config import Settings
    from vocab.main import create_app

    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        create_app(Settings(_env_file=None, session_secret=""))
