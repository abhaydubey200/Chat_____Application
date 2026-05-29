"""
Fix script: Downgrade existing users who incorrectly have admin roles.

Before the fix (see services/auth_service.py change), new users signing up were
assigned ROLE_ADMIN instead of ROLE_EMPLOYEE. This script finds all users who
currently hold admin-level roles (super_admin, admin, security_admin) — except
the designated admin user (admin@dushman.ai) — and downgrades them to "employee".

Safe to run multiple times (idempotent).

Usage:
    python fix_existing_admins.py              # Preview changes (dry-run)
    python fix_existing_admins.py --apply      # Apply changes
"""

import asyncio
import sys

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.db.models import OrgMembership, User

# The only user allowed to hold admin-level roles
ADMIN_EMAIL = "admin@dushman.ai"

# Roles that are considered "admin-level" and should only belong to the admin user
ADMIN_ROLES = {"super_admin", "admin", "security_admin"}

# The role regular users should have
TARGET_ROLE = "employee"


async def get_admin_user_id(db: AsyncSession) -> str | None:
    """Look up the admin user's UUID by email."""
    stmt = select(User.id).where(User.email == ADMIN_EMAIL, User.is_active.is_(True))
    result = await db.execute(stmt)
    row = result.one_or_none()
    return str(row[0]) if row else None


async def find_violations(db: AsyncSession) -> list[dict]:
    """
    Find all OrgMembership records where a non-admin user holds an admin role.

    Returns a list of dicts with user info for reporting.
    """
    # Get admin user ID to exclude them
    admin_id = await get_admin_user_id(db)

    stmt = (
        select(
            OrgMembership.id.label("membership_id"),
            OrgMembership.organization_id,
            OrgMembership.role,
            OrgMembership.user_id,
            User.email,
            User.created_at,
        )
        .join(User, User.id == OrgMembership.user_id)
        .where(
            OrgMembership.role.in_(ADMIN_ROLES),
            OrgMembership.is_active.is_(True),
        )
        .order_by(User.email)
    )

    result = await db.execute(stmt)
    rows = result.all()

    violations = []
    for row in rows:
        uid = str(row.user_id)
        # Skip the designated admin user
        if admin_id and uid == admin_id:
            continue
        violations.append({
            "membership_id": str(row.membership_id),
            "user_id": uid,
            "email": row.email,
            "role": row.role,
            "created_at": str(row.created_at),
        })

    return violations


async def apply_fix(db: AsyncSession, violations: list[dict]) -> int:
    """Downgrade all violating memberships to employee role."""
    membership_ids = [v["membership_id"] for v in violations]
    if not membership_ids:
        return 0

    stmt = (
        update(OrgMembership)
        .where(OrgMembership.id.in_(membership_ids))
        .values(role=TARGET_ROLE)
    )
    await db.execute(stmt)
    await db.commit()
    return len(membership_ids)


async def main():
    is_dry_run = "--apply" not in sys.argv

    if is_dry_run:
        print("🔍 DRY RUN MODE — no changes will be made.")
        print("   Run with --apply to commit changes.\n")
    else:
        print("⚠️  APPLY MODE — changes WILL be written to the database.\n")

    print(f"Admin email (preserved): {ADMIN_EMAIL}")
    print(f"Admin roles: {', '.join(sorted(ADMIN_ROLES))}")
    print(f"Target role for others: {TARGET_ROLE}")
    print()

    async with AsyncSessionLocal() as db:
        violations = await find_violations(db)

        if not violations:
            print("✅ No violations found — all non-admin users already have correct roles.")
            return

        # Print summary table
        print(f"Found {len(violations)} user(s) with incorrect admin roles:\n")
        print(f"  {'Email':<40} {'Current Role':<20} {'Created At':<25}")
        print(f"  {'─' * 40} {'─' * 20} {'─' * 25}")
        for v in violations:
            print(f"  {v['email']:<40} {v['role']:<20} {v['created_at']:<25}")

        print()

        if is_dry_run:
            print("ℹ️  Run with --apply to downgrade these users to 'employee'.")
            return

        # Apply the fix
        count = await apply_fix(db, violations)
        print(f"✅ Successfully downgraded {count} user(s) from admin role to '{TARGET_ROLE}'.")

        # Verify
        remaining = await find_violations(db)
        if remaining:
            print(f"⚠️  {len(remaining)} violation(s) still remain (may need investigation):")
            for v in remaining:
                print(f"   - {v['email']} ({v['role']})")
        else:
            print("✅ All violations cleared.")


if __name__ == "__main__":
    asyncio.run(main())
