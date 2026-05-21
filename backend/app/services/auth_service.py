from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.db.repositories.user_repository import UserRepository
from app.core import security
from app.db.models import User

class AuthService:
    @staticmethod
    async def signup(db: AsyncSession, email: str, password: str) -> User:
        """Register a new user."""
        existing_user = await UserRepository.get_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists."
            )
        
        password_hash = security.get_password_hash(password)
        user = await UserRepository.create(db, email, password_hash)
        return user

    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> dict:
        """Authenticate user and return access token."""
        user = await UserRepository.get_by_email(db, email)
        if not user or not security.verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = security.create_access_token(subject=user.id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email
            }
        }
