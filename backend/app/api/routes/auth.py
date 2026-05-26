from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.limiter import limiter
from app.api.dependencies import get_current_user
from app.api.schemas import UserSignup, UserLogin, TokenResponse, UserResponse
from app.api.controllers.auth_controller import AuthController
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserResponse)
@limiter.limit("10/minute")
async def signup(signup_data: UserSignup, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new account."""
    return await AuthController.signup(db, signup_data)

@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(login_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate credentials and generate JWT."""
    return await AuthController.login(db, login_data)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve logged-in user profile details."""
    return await AuthController.get_me(current_user)
