from fastapi.testclient import TestClient

from entrypoints.foundation_api.main import create_app


def test_health_surface_is_independent_of_feature_routes(settings, database):
    app = create_app(settings, database)
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
        assert response.headers["x-request-id"].startswith("req_")
        assert client.get("/api/console/v1/auth/login").status_code == 404


def test_failed_database_readiness_returns_sanitized_error(settings):
    class BrokenDatabase:
        def session(self):
            raise RuntimeError("database-password-must-never-be-public")

    with TestClient(create_app(settings, BrokenDatabase())) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["code"] == "SERVICE_UNAVAILABLE"
        assert "database-password-must-never-be-public" not in response.text
