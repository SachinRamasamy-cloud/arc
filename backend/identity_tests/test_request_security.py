from .conftest import PASSWORD, PREFIX, call, verified_login


def test_mutations_require_csrf(ctx):
    response = ctx["client"].post(PREFIX + "/signup", json={"email": "member@example.com", "name": "Member", "password": PASSWORD, "accept_terms": True})
    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"
    assert response.headers["x-request-id"] == response.json()["request_id"]


def test_untrusted_origin_is_rejected(ctx):
    response = call(ctx["client"], "POST", "/login", json={"email": "member@example.com", "password": PASSWORD}, headers={"Origin": "https://untrusted.example"})
    assert response.status_code == 403
    assert response.json()["code"] == "ORIGIN_BLOCKED"


def test_request_body_limit_is_enforced(ctx):
    ctx["settings"].max_body_bytes = 128
    response = call(ctx["client"], "POST", "/login", content="x" * 129)
    assert response.status_code == 413
    assert response.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_empty_mutation_body_returns_validation_error(ctx):
    response = call(ctx["client"], "POST", "/login", content=b"")
    assert response.status_code == 422


def test_validation_errors_do_not_echo_submitted_password(ctx):
    secret = "a-sensitive-value-that-must-not-be-echoed"
    response = call(ctx["client"], "POST", "/login", json={"email": "invalid-email", "password": secret})
    assert response.status_code == 422
    assert secret not in response.text


def test_signup_is_rate_limited(ctx):
    for index in range(6):
        response = call(ctx["client"], "POST", "/signup", json={"email": f"member{index}@example.com", "name": "Member", "password": PASSWORD, "accept_terms": True})
    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"


def test_health_and_surface_scope(ctx):
    client = ctx["client"]
    assert client.get("/health/ready").status_code == 200
    assert client.get("/api/console/v1/workspaces").status_code == 404
    assert client.get("/api/operator/v1/auth/me").status_code == 404


def test_csrf_token_from_before_login_cannot_modify_authenticated_session(ctx):
    client = ctx["client"]
    old_token = client.get(PREFIX + "/csrf").json()["csrf_token"]
    verified_login(ctx)
    response = client.patch(PREFIX + "/preferences", json={"compact": True}, headers={"X-CSRF-Token": old_token})
    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_FAILED"
