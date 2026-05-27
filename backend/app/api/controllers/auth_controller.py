from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
from fastapi import HTTPException, status
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.services.security_event_service import SecurityEventService
from app.api.schemas import UserSignup, UserLogin, TokenResponse, UserResponse
from app.db.models import User

class AuthController:
    @staticmethod
    async def signup(db: AsyncSession, signup_data: UserSignup) -> UserResponse:
        """Controller to sign up a new user."""
        user = await AuthService.signup(db, signup_data.email, signup_data.password)
        AuditService.append_background(
            event_type="signup",
            status="success",
            user_id=user.id,
            organization_id=user.organization_id,
        )
        return user

    @staticmethod
    async def login(db: AsyncSession, login_data: UserLogin, client_ip: str | None = None, user_agent: str | None = None) -> TokenResponse:
        """Controller to log in user and return JWT."""
        try:
            login_result = await AuthService.login(db, login_data.email, login_data.password)
            AuditService.append_background(
                event_type="login",
                status="success",
                user_id=login_result["user"]["id"],
                metadata={"email_hash": hashlib.sha256(login_data.email.lower().encode()).hexdigest()},
                ip_address=client_ip,
                user_agent=user_agent,
            )
            return login_result
        except HTTPException as exc:
            if exc.status_code == status.HTTP_401_UNAUTHORIZED:
                await SecurityEventService.record_event(
                    event_type="auth_failed_login",
                    severity="medium",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    metadata={"email_hash": hashlib.sha256(login_data.email.lower().encode()).hexdigest()},
                )
                AuditService.append_background(
                    event_type="login",
                    status="failure",
                    metadata={"email_hash": hashlib.sha256(login_data.email.lower().encode()).hexdigest()},
                    ip_address=client_ip,
                    user_agent=user_agent,
                )
            raise

    @staticmethod
    async def get_me(current_user: User) -> UserResponse:
        """Controller to fetch currently logged-in user profile."""
        return current_user

    @staticmethod
    async def logout(current_user: User) -> dict:
        AuditService.append_background(
            event_type="logout",
            status="success",
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        return {"status": "success"}
