def signup(client, email="user@example.com", password="correcthorsebatterystaple"):
    return client.post("/signup", json={"email": email, "password": password})


def login(client, email="user@example.com", password="correcthorsebatterystaple"):
    return client.post("/login", json={"email": email, "password": password})


def test_signup_success(client):
    response = signup(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert "id" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_signup_lowercases_email(client):
    response = signup(client, email="MixedCase@Example.com")
    assert response.status_code == 201
    assert response.json()["email"] == "mixedcase@example.com"


def test_signup_duplicate_email_returns_409(client):
    signup(client)
    response = signup(client)
    assert response.status_code == 409


def test_signup_duplicate_email_case_insensitive(client):
    signup(client, email="user@example.com")
    response = signup(client, email="User@Example.com")
    assert response.status_code == 409


def test_signup_rejects_short_password(client):
    response = signup(client, password="short")
    assert response.status_code == 422


def test_login_success_returns_tokens(client):
    signup(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900


def test_login_wrong_password_returns_401(client):
    signup(client)
    response = login(client, password="wrongpassword")
    assert response.status_code == 401


def test_login_nonexistent_email_returns_401(client):
    response = login(client, email="nobody@example.com")
    assert response.status_code == 401


def test_login_errors_do_not_distinguish_missing_user_from_wrong_password(client):
    signup(client)
    wrong_password = login(client, password="wrongpassword")
    no_such_user = login(client, email="nobody@example.com")
    assert wrong_password.json() == no_such_user.json()


def test_refresh_issues_valid_access_token_for_same_user(client):
    from app.security import decode_access_token

    signup_body = signup(client).json()
    tokens = login(client).json()

    response = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200

    new_access_token = response.json()["access_token"]
    payload = decode_access_token(new_access_token)
    assert payload["sub"] == signup_body["id"]


def test_refresh_rotates_the_refresh_token(client):
    signup(client)
    tokens = login(client).json()

    response = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["refresh_token"] != tokens["refresh_token"]


def test_refresh_old_token_rejected_after_rotation(client):
    signup(client)
    tokens = login(client).json()

    client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})

    reused = client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_refresh_reuse_of_rotated_token_revokes_whole_family(client):
    signup(client)
    original = login(client).json()

    rotated = client.post(
        "/refresh", json={"refresh_token": original["refresh_token"]}
    ).json()

    # Reusing the already-rotated (original) token is theft evidence — this
    # should revoke every active token for the user, including the "new"
    # one that a legitimate client would actually be holding.
    reuse_response = client.post(
        "/refresh", json={"refresh_token": original["refresh_token"]}
    )
    assert reuse_response.status_code == 401

    legitimate_refresh = client.post(
        "/refresh", json={"refresh_token": rotated["refresh_token"]}
    )
    assert legitimate_refresh.status_code == 401


def test_refresh_rejects_unknown_token(client):
    response = client.post("/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401


def test_logout_revokes_refresh_token(client):
    signup(client)
    tokens = login(client).json()

    logout_response = client.post(
        "/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 401


def test_jwks_endpoint_returns_public_key(client):
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    keys = response.json()["keys"]
    assert len(keys) == 1
    assert keys[0]["kty"] == "RSA"
    assert keys[0]["alg"] == "RS256"
    assert keys[0]["use"] == "sig"
    assert "kid" in keys[0]


def test_me_returns_current_user(client):
    signup_body = signup(client).json()
    tokens = login(client).json()

    response = client.get(
        "/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == signup_body["id"]
    assert response.json()["email"] == signup_body["email"]


def test_me_without_token_is_rejected(client):
    response = client.get("/me")
    assert response.status_code in (401, 403)


def test_me_with_garbage_token_returns_401(client):
    response = client.get("/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401


def test_me_with_refresh_token_instead_of_access_token_returns_401(client):
    # A refresh token is an opaque random string, not a JWT — /me must
    # reject it rather than accidentally accepting the wrong credential type.
    signup(client)
    tokens = login(client).json()

    response = client.get(
        "/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert response.status_code == 401


def test_logout_is_idempotent(client):
    signup(client)
    tokens = login(client).json()

    first = client.post("/logout", json={"refresh_token": tokens["refresh_token"]})
    second = client.post("/logout", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 204
    assert second.status_code == 204


def test_logout_unknown_token_is_a_no_op(client):
    response = client.post("/logout", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 204
