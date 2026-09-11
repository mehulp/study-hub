import uuid
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import OAuthClient, RefreshToken, User
from app.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ServiceTokenRequest,
    ServiceTokenResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    ACCESS_TOKEN_TTL,
    REFRESH_TOKEN_TTL,
    SERVICE_TOKEN_TTL,
    create_access_token,
    create_service_token,
    decode_access_token,
    generate_refresh_token,
    get_jwks,
    hash_password,
    hash_refresh_token,
    verify_client_secret_or_dummy,
    verify_password_or_dummy,
)

app = FastAPI(title="Auth Service")
bearer_scheme = HTTPBearer()


@app.get("/.well-known/jwks.json")
def jwks() -> dict:
    return get_jwks()


@app.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> User:
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    db.refresh(user)
    return user


def _create_refresh_token(user_id, db: Session) -> tuple[RefreshToken, str]:
    """Insert a new refresh_tokens row (not yet committed) and return it
    alongside the plaintext token — the only place that plaintext exists."""
    plaintext = generate_refresh_token()
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(plaintext),
        expires_at=datetime.now(timezone.utc) + REFRESH_TOKEN_TTL,
    )
    db.add(row)
    db.flush()  # assigns row.id (server-generated) without ending the transaction
    return row, plaintext


def _issue_tokens(user: User, db: Session) -> TokenResponse:
    access_token = create_access_token(user.id)
    _, refresh_token = _create_refresh_token(user.id, db)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )


@app.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()

    # verify_password_or_dummy always runs a real Argon2id verification,
    # even when no user was found, so /login's latency can't be used to
    # enumerate which emails are registered (see security.py).
    password_valid = verify_password_or_dummy(
        payload.password, user.password_hash if user is not None else None
    )
    if user is None or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return _issue_tokens(user, db)


@app.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    now = datetime.now(timezone.utc)

    # A token revoked *by rotation* (replaced_by_id set) being presented
    # again means someone is using a token that should no longer exist on
    # any legitimate client — the strongest signal we have of theft. Revoke
    # every still-active token for this user, forcing full re-login
    # (Decision #28).
    if stored is not None and stored.revoked_at is not None and stored.replaced_by_id is not None:
        db.query(RefreshToken).filter(
            RefreshToken.user_id == stored.user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": now})
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token = create_access_token(stored.user_id)
    new_row, new_refresh_token = _create_refresh_token(stored.user_id, db)
    stored.revoked_at = now
    stored.replaced_by_id = new_row.id
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )


@app.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


@app.get("/me", response_model=UserResponse)
def me(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    user = db.query(User).filter(User.id == uuid.UUID(payload["sub"])).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    return user


@app.post("/oauth/token", response_model=ServiceTokenResponse)
def issue_service_token(
    payload: ServiceTokenRequest, db: Session = Depends(get_db)
) -> ServiceTokenResponse:
    client = db.query(OAuthClient).filter(OAuthClient.client_id == payload.client_id).first()

    # Same anti-enumeration reasoning as /login: always run the comparison,
    # even when no client_id was found, and return the same generic error
    # either way (Decision #41).
    secret_valid = verify_client_secret_or_dummy(
        payload.client_secret, client.client_secret_hash if client is not None else None
    )
    if client is None or not secret_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client credentials"
        )

    access_token = create_service_token(client.client_id)
    return ServiceTokenResponse(
        access_token=access_token, expires_in=int(SERVICE_TOKEN_TTL.total_seconds())
    )
