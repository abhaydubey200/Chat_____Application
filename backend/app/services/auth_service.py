import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.organization_repository import OrganizationRepository
from app.db.repositories.org_membership_repository import OrgMembershipRepository
from app.core.rbac import ROLE_EMPLOYEE
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
        org_name = f"{email.split('@')[0]}'s Org"
        organization = await OrganizationRepository.create(db, org_name)
        user = await UserRepository.create(db, email, password_hash, organization_id=organization.id)
        await OrgMembershipRepository.create(db, organization.id, user.id, ROLE_EMPLOYEE)
        await db.commit()
        await db.refresh(user)
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
        
        session_id = str(uuid.uuid4())
        role = ROLE_EMPLOYEE
        org_id = str(user.organization_id) if user.organization_id else None
        if user.organization_id:
            membership = await OrgMembershipRepository.get_by_user_and_org(db, user.id, user.organization_id)
            if membership:
                role = membership.role
        access_token = security.create_access_token(
            subject=user.id,
            extra_claims={
                "sid": session_id,
                "org_id": org_id,
                "role": role,
            },
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": role,
            }
        }
