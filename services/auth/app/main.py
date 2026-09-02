from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import SignupRequest, UserResponse
from app.security import hash_password

app = FastAPI(title="Auth Service")


@app.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> User:
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
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
