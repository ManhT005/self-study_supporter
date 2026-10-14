from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api.app.main import COOKIE, HTTPSettings, create_app
from apps.api.app.security import Sessions
from study_supporter.application.use_cases.authenticate import Authentication


class Users:
    def __init__(self):
        self.users = {}

    def register(self, username, password):
        self.users[username] = (str(len(self.users) + 1), password)
        return self.users[username][0]

    def authenticate(self, username, password):
        entry = self.users.get(username)
        return entry[0] if entry and entry[1] == password else None


@contextmanager
def client(secure=False, ttl=28800):
    calls = []
    factory = SimpleNamespace(
        authentication=Authentication(Users()),
        documents=SimpleNamespace(),
        verify_schema=lambda: calls.append("verify"),
        close=lambda: calls.append("close"),
    )
    app = create_app(lambda: factory, HTTPSettings("https://testserver", secure, ttl))
    with TestClient(
        app, base_url="https://testserver", headers={"origin": "https://testserver"}
    ) as http:
        yield http, calls
    assert calls[-1] == "close"


def register_login(http, username="alice"):
    credentials = {"username": username, "password": "secret-pass"}
    assert http.post("/api/v1/auth/register", json=credentials).status_code == 201
    return http.post("/api/v1/auth/login", json=credentials)


def test_rotation_logout_expiry_and_secure_cookie():
    with client(secure=True) as (http, calls):
        assert http.get("/api/v1/auth/me").status_code == 401
        login = register_login(http)
        assert login.status_code == 200
        cookie = login.headers["set-cookie"]
        for flag in ["HttpOnly", "Secure", "SameSite=lax", "Max-Age=28800"]:
            assert flag in cookie
        old_token = http.cookies.get(COOKIE)
        assert http.get("/api/v1/auth/me").json() == {"username": "alice"}
        register_login(http)
        assert http.app.state.sessions.get(old_token) is None
        assert http.post("/api/v1/auth/logout").status_code == 204
        assert http.get("/api/v1/auth/me").status_code == 401
        assert http.get("/health/ready").status_code == 200
        assert "verify" in calls
    with client(ttl=-1) as (http, _):
        register_login(http)
        assert http.get("/api/v1/auth/me").status_code == 401


def test_origin_spoofing_invalid_credentials_and_rate_limit():
    with client() as (http, _):
        body = {"username": "alice", "password": "secret-pass"}
        assert (
            http.post(
                "/api/v1/auth/login", json=body, headers={"origin": "https://evil.test"}
            ).status_code
            == 403
        )
        assert http.post("/api/v1/auth/login", json={**body, "user_id": "1"}).status_code == 422
        assert http.post("/api/v1/auth/login", json=body).status_code == 401
        for _ in range(12):
            response = http.post("/api/v1/auth/login", json=body)
        assert response.status_code == 429
        assert response.json()["request_id"] == response.headers["x-request-id"]
        assert set(response.json()) == {"code", "message", "request_id"}


def test_tokens_are_hashed_and_expired():
    from study_supporter.application.contracts.context import AppContext

    now = [0]
    sessions = Sessions(ttl=10, clock=lambda: now[0])
    token = sessions.issue(AppContext("1"), "alice")
    assert token not in sessions.entries
    assert sessions.get(token).context.user_id == "1"
    now[0] = 10
    assert sessions.get(token) is None
