"""
Test username:password authentication mechanism.
"""

from pytest_mock import MockerFixture
from requests_mock.mocker import Mocker
from yarl import URL

from preset_cli.auth.superset import SupersetJWTAuth, UsernamePasswordAuth


def test_username_password_auth(requests_mock: Mocker) -> None:
    """
    Tests for the username/password authentication mechanism using security API.
    """
    access_token = "test_access_token_12345"
    csrf_token = "test_csrf_token"

    # Mock the security login endpoint
    requests_mock.post(
        "https://superset.example.org/api/v1/security/login",
        json={"access_token": access_token},
    )

    # Mock the CSRF token endpoint
    requests_mock.get(
        "https://superset.example.org/api/v1/security/csrf_token",
        json={"result": csrf_token},
    )

    auth = UsernamePasswordAuth(
        URL("https://superset.example.org/"),
        "admin",
        "password123",
    )

    # Should now use JWT auth headers
    headers = auth.get_headers()
    assert headers == {
        "Authorization": f"Bearer {access_token}",
        "X-CSRFToken": csrf_token,
    }

    # Verify the login request payload
    login_request = requests_mock.request_history[0]
    assert login_request.json() == {
        "username": "admin",
        "password": "password123",
        "provider": "db",
    }


def test_jwt_auth_superset(mocker: MockerFixture) -> None:
    """
    Test the ``JWTAuth`` authentication mechanism for Superset tenant.
    """
    auth = SupersetJWTAuth("my-token", URL("https://example.org/"))
    mocker.patch.object(auth, "get_csrf_token", return_value="myCSRFToken")

    assert auth.get_headers() == {
        "Authorization": "Bearer my-token",
        "X-CSRFToken": "myCSRFToken",
    }


def test_get_csrf_token(requests_mock: Mocker) -> None:
    """
    Test the get_csrf_token method.
    """
    auth = SupersetJWTAuth("my-token", URL("https://example.org/"))
    requests_mock.get(
        "https://example.org/api/v1/security/csrf_token",
        json={"result": "myCSRFToken"},
    )

    assert auth.get_csrf_token("my-token") == "myCSRFToken"
