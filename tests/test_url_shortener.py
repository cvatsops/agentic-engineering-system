
from fastapi.testclient import TestClient

from app.url_shortener import create_app


def test_create_redirect_and_track_clicks(tmp_path):
    app = create_app(tmp_path / "test.db")

    with TestClient(app) as client:
        response = client.post(
            "/urls",
            json={"original_url": "https://example.com/docs"},
        )

        assert response.status_code == 201

        data = response.json()
        code = data["short_code"]

        assert data["original_url"] == "https://example.com/docs"
        assert data["short_url"] == f"/{code}"

        # Redirect should increment the click count.
        redirect = client.get(f"/{code}", follow_redirects=False)
        assert redirect.status_code == 307
        assert redirect.headers["location"] == "https://example.com/docs"

        analytics = client.get(f"/urls/{code}/analytics")
        assert analytics.status_code == 200
        assert analytics.json()["click_count"] == 1

        client.get(f"/{code}", follow_redirects=False)

        analytics = client.get(f"/urls/{code}/analytics")
        assert analytics.json()["click_count"] == 2


def test_unknown_short_code_returns_404(tmp_path):
    app = create_app(tmp_path / "test.db")

    with TestClient(app) as client:
        response = client.get("/does-not-exist")

        assert response.status_code == 404


def test_unknown_analytics_returns_404(tmp_path):
    app = create_app(tmp_path / "test.db")

    with TestClient(app) as client:
        response = client.get("/urls/unknown/analytics")

        assert response.status_code == 404


def test_health_endpoint(tmp_path):
    app = create_app(tmp_path / "test.db")

    with TestClient(app) as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


def test_url_persists_across_app_instances(tmp_path):
    database = tmp_path / "persistent.db"

    with TestClient(create_app(database)) as first_client:
        response = first_client.post(
            "/urls",
            json={"original_url": "https://example.com"},
        )
        code = response.json()["short_code"]

    # A new app instance uses the same database file.
    with TestClient(create_app(database)) as second_client:
        analytics = second_client.get(
            f"/urls/{code}/analytics"
        )

        assert analytics.status_code == 200
        assert analytics.json()["original_url"] == "https://example.com/"
        assert analytics.json()["click_count"] == 0