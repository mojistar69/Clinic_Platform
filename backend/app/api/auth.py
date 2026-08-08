from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


from app.database.database import get_db
from app.models.user import User

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse
)

from app.auth.security import (
    hash_password,
    verify_password
)

from app.auth.jwt import (
    create_access_token
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)



@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    exists = (
        db.query(User)
        .filter(
            User.mobile == user.mobile
        )
        .first()
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail="Mobile already registered"
        )


    new_user = User(
        mobile=user.mobile,
        full_name=user.full_name,
        password_hash=hash_password(
            user.password
        )
    )


    db.add(new_user)
    db.commit()
    db.refresh(new_user)


    return new_user



@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    user: UserLogin,
    db: Session = Depends(get_db)
):

    db_user = (
        db.query(User)
        .filter(
            User.mobile == user.mobile
        )
        .first()
    )


    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid mobile or password"
        )


    if not verify_password(
        user.password,
        db_user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid mobile or password"
        )


    token = create_access_token(
        {
            "user_id": db_user.id,
            "role": db_user.role
        }
    )


    return {
        "access_token": token,
        "token_type": "bearer"
    }