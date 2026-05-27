from typing import Iterable

ROLE_EMPLOYEE = "employee"
ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"
ROLE_SECURITY_ADMIN = "security_admin"
ROLE_SUPER_ADMIN = "super_admin"

PERMISSION_CHAT = "chat.use"
PERMISSION_CONVERSATIONS_READ = "conversations.read"
PERMISSION_AUDIT_READ = "audit.read"
PERMISSION_ANALYTICS_READ = "analytics.read"
PERMISSION_SECURITY_READ = "security.read"
PERMISSION_PROVIDER_MANAGE = "provider.manage"
PERMISSION_MODEL_MANAGE = "model.manage"
PERMISSION_RETENTION_MANAGE = "retention.manage"
PERMISSION_DLP_MANAGE = "dlp.manage"
PERMISSION_USER_MANAGE = "user.manage"

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_EMPLOYEE: {
        PERMISSION_CHAT,
        PERMISSION_CONVERSATIONS_READ,
    },
    ROLE_MANAGER: {
        PERMISSION_CHAT,
        PERMISSION_CONVERSATIONS_READ,
        PERMISSION_ANALYTICS_READ,
    },
    ROLE_ADMIN: {
        PERMISSION_CHAT,
        PERMISSION_CONVERSATIONS_READ,
        PERMISSION_ANALYTICS_READ,
        PERMISSION_AUDIT_READ,
        PERMISSION_PROVIDER_MANAGE,
        PERMISSION_MODEL_MANAGE,
        PERMISSION_RETENTION_MANAGE,
        PERMISSION_DLP_MANAGE,
        PERMISSION_USER_MANAGE,
    },
    ROLE_SECURITY_ADMIN: {
        PERMISSION_CHAT,
        PERMISSION_CONVERSATIONS_READ,
        PERMISSION_ANALYTICS_READ,
        PERMISSION_AUDIT_READ,
        PERMISSION_SECURITY_READ,
        PERMISSION_DLP_MANAGE,
    },
    ROLE_SUPER_ADMIN: {
        "*",
    },
}

def has_permission(role: str | None, permission: str) -> bool:
    if not role:
        return False
    permissions = ROLE_PERMISSIONS.get(role, set())
    return "*" in permissions or permission in permissions

def role_allows_any(role: str | None, permissions: Iterable[str]) -> bool:
    return any(has_permission(role, perm) for perm in permissions)
