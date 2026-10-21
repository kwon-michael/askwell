from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import Credentials, Token, UserOut
from ..security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(creds: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == creds.username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username taken")
    user = User(username=creds.username, password_hash=hash_password(creds.password))
    db.add(user)
    db.commit()
    return Token(access_token=create_token(user.id))


@router.post("/login", response_model=Token)
def login(creds: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == creds.username))
    if user is None or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password")
    return Token(access_token=create_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, username=user.username)
