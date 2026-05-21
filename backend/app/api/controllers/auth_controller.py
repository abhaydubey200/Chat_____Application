from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth_service import AuthService
from app.api.schemas import UserSignup, UserLogin, TokenResponse, UserResponse
from app.db.models import User

class AuthController:
    @staticmethod
    async def signup(db: AsyncSession, signup_data: UserSignup) -> UserResponse:
        """Controller to sign up a new user."""
        user = await AuthService.signup(db, signup_data.email, signup_data.password)
        return user

    @staticmethod
    async def login(db: AsyncSession, login_data: UserLogin) -> TokenResponse:
        """Controller to log in user and return JWT."""
        login_result = await AuthService.login(db, login_data.email, login_data.password)
        return login_result

    @staticmethod
    async def get_me(current_user: User) -> UserResponse:
        """Controller to fetch currently logged-in user profile."""
        return current_user
