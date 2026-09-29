"""POST /api/auth/register, POST /api/auth/login"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.schemas import LoginIn, RegisterIn
from backend.models.tables import User
from cloud.auth_service import create_access_token, hash_password, verify_password
from cloud.database_service import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    user = User(name=body.name, email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return {"access_token": create_access_token(user.user_id), "token_type": "bearer",
            "user": {"user_id": user.user_id, "name": user.name, "email": user.email}}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_access_token(user.user_id), "token_type": "bearer",
            "user": {"user_id": user.user_id, "name": user.name, "email": user.email}}
