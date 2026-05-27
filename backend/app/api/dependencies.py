import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import security
from app.core.observability import get_request_context
from app.core.rbac import has_permission
from app.core.database import get_db
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.org_membership_repository import OrgMembershipRepository
from app.db.models import User

# Standard OAuth2 Password Bearer scheme. Frontend sends token as authorization header Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Verifies JWT access token and resolves current active user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = security.decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    user_id_str: str = payload.get("sub")
    session_id: str | None = payload.get("sid")
    org_id: str | None = payload.get("org_id")
    role: str | None = payload.get("role")
    if user_id_str is None:
        raise credentials_exception
        
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception
        
    user = await UserRepository.get_by_id(db, user_id)
    if user is None:
        raise credentials_exception

    ctx = get_request_context()
    if ctx:
        ctx.user_id = str(user.id)
        ctx.session_id = session_id
        ctx.organization_id = org_id or (str(user.organization_id) if user.organization_id else None)
        ctx.role = role
        
    return user

async def get_current_membership(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization assigned.")
    membership = await OrgMembershipRepository.get_by_user_and_org(db, user.id, user.organization_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied.")
    return membership

def require_permission(permission: str):
    async def _require(
        membership = Depends(get_current_membership)
    ):
        if not has_permission(membership.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return membership
    return _require
