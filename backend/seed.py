"""
Seed script for Dushman AI — PostgreSQL.

Creates the governance schema, all application tables, and
inserts a comprehensive set of default / seed data for local
development.

Usage:
    python seed.py

Requirements:
    - PostgreSQL must be running (e.g. via Docker)
    - .env must have a valid DATABASE_URL
    - Backend dependencies must be installed
"""

import asyncio
import uuid
from datetime import datetime, timedelta, date

from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal, Base
from app.core.security import get_password_hash
from app.db.models import (
    Organization,
    User,
    OrgMembership,
    Conversation,
    Message,
    AuditLog,
    UsageEvent,
    DlpRule,
    DlpEvent,
    SecurityEvent,
    ProviderPolicy,
    ModelPolicy,
    RetentionPolicy,
    UsageDailyAggregate,
)

# ── Hard-coded UUIDs for determinism in development ──────────────
ORG_ID     = uuid.UUID("00000000-0000-0000-0000-000000000001")
ADMIN_ID   = uuid.UUID("00000000-0000-0000-0000-000000000010")
USER_ID    = uuid.UUID("00000000-0000-0000-0000-000000000011")
MANAGER_ID = uuid.UUID("00000000-0000-0000-0000-000000000012")
CONV_ID    = uuid.UUID("00000000-0000-0000-0000-000000000020")

# ── Seed data helpers ────────────────────────────────────────────

DEFAULT_DLP_RULES = [
    {
        "name": "JWT token",
        "description": "Detect JWT token patterns (three base64 segments)",
        "rule_type": "regex",
        "pattern": r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}",
        "action": "block",
        "severity": "high",
    },
    {
        "name": "API key / secret assignment",
        "description": "Detect inline API key, token, or password assignments",
        "rule_type": "regex",
        "pattern": r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[\"']?([a-zA-Z0-9_\-\.]{12,})",
        "action": "block",
        "severity": "high",
    },
    {
        "name": "SSH private key",
        "description": "Detect private key PEM blocks",
        "rule_type": "regex",
        "pattern": r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "Database connection string",
        "description": "Detect postgres:// connection strings",
        "rule_type": "regex",
        "pattern": r"(?i)postgres(?:ql)?://[^\s]+",
        "action": "block",
        "severity": "high",
    },
    {
        "name": "Credit card pattern",
        "description": "Detect potential credit card numbers (13-19 digits)",
        "rule_type": "regex",
        "pattern": r"\b(?:\d[ -]*?){13,19}\b",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "Aadhaar number",
        "description": "Detect Indian Aadhaar (XXXX XXXX XXXX)",
        "rule_type": "regex",
        "pattern": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "PAN number",
        "description": "Detect Indian PAN (AAAAA9999A)",
        "rule_type": "regex",
        "pattern": r"\b[A-Z]{5}\d{4}[A-Z]\b",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "Internal / private URL",
        "description": "Detect private IP / localhost URLs",
        "rule_type": "regex",
        "pattern": r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)[^\s]*",
        "action": "warn",
        "severity": "medium",
    },
    {
        "name": "Confidential keywords",
        "description": "Detect confidentiality / secrecy indicators",
        "rule_type": "keyword",
        "pattern": "confidential,internal use only,do not share,private,secret,proprietary",
        "action": "warn",
        "severity": "medium",
    },
    {
        "name": "AWS secret key",
        "description": "Detect AWS secret access keys",
        "rule_type": "regex",
        "pattern": r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*[\"']?[a-zA-Z0-9/+=]{40}",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "GitHub token",
        "description": "Detect GitHub personal access tokens",
        "rule_type": "regex",
        "pattern": r"(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36}",
        "action": "block",
        "severity": "high",
    },
    {
        "name": "High-entropy secret (fallback)",
        "description": "Entropy-based detection of likely secrets ≥16 chars",
        "rule_type": "entropy",
        "pattern": "4.2",
        "action": "warn",
        "severity": "medium",
    },
]

# NVIDIA pricing per 1K tokens (USD) — approximate as of mid-2026
MODEL_PRICING = [
    ("meta/llama-3.1-70b-instruct",               0.00090, 0.00090),
    ("meta/llama-3-8b-instruct",                  0.00020, 0.00020),
    ("nvidia/llama-3.1-nemotron-70b-instruct",     0.00100, 0.00100),
]

RETENTION_CONFIGS = [
    ("conversations", 30,  90),
    ("messages",      30,  90),
    ("audit",         365, 730),
    ("usage",         365, 730),
    ("dlp",           365, 730),
    ("security",      365, 730),
]

# ── Helpers ──────────────────────────────────────────────────────

def now():
    return datetime.utcnow()


async def row_exists(table, **filters) -> bool:
    stmt = select(func.count()).select_from(table)
    for col, val in filters.items():
        stmt = stmt.where(getattr(table, col) == val)
    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
        return result.scalar() > 0


async def upsert(table, rows: list[dict], index_elements: list[str]):
    """Upsert helper for asyncpg-style ON CONFLICT DO NOTHING."""
    if not rows:
        return
    async with AsyncSessionLocal() as session:
        stmt = pg_insert(table).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
        await session.execute(stmt)
        await session.commit()


# ── Seed sections ────────────────────────────────────────────────

async def seed_governance_schema():
    """Ensure the 'governance' schema exists (tables created by init_db)."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS governance"))
    print("✓ governance schema present")


async def seed_default_organization():
    if await row_exists(Organization, id=ORG_ID):
        print("→ Organization already exists, skipping")
        return
    org = Organization(
        id=ORG_ID,
        name="Dushman AI",
        is_active=True,
    )
    async with AsyncSessionLocal() as session:
        session.add(org)
        await session.commit()
    print("✓ Default organization created")


async def seed_users():
    """Create admin, manager, and regular user accounts."""
    users = [
        {
            "id": ADMIN_ID,
            "email": "admin@dushman.ai",
            "password": "Admin@123",
            "organization_id": ORG_ID,
        },
        {
            "id": USER_ID,
            "email": "user@dushman.ai",
            "password": "User@123",
            "organization_id": ORG_ID,
        },
        {
            "id": MANAGER_ID,
            "email": "manager@dushman.ai",
            "password": "Manager@123",
            "organization_id": ORG_ID,
        },
    ]
    rows = []
    for u in users:
        if await row_exists(User, id=u["id"]):
            print(f"  → User {u['email']} exists, skipping")
            continue
        rows.append(
            {
                "id": u["id"],
                "email": u["email"],
                "password_hash": get_password_hash(u["password"]),
                "organization_id": u["organization_id"],
                "is_active": True,
            }
        )
    if not rows:
        return
    async with AsyncSessionLocal() as session:
        session.add_all(User(**r) for r in rows)
        await session.commit()
    print(f"✓ {len(rows)} user(s) created")


async def seed_org_memberships():
    memberships = [
        {"organization_id": ORG_ID, "user_id": ADMIN_ID,   "role": "super_admin"},
        {"organization_id": ORG_ID, "user_id": USER_ID,    "role": "employee"},
        {"organization_id": ORG_ID, "user_id": MANAGER_ID,  "role": "manager"},
    ]
    rows = []
    for m in memberships:
        if await row_exists(OrgMembership, organization_id=ORG_ID, user_id=m["user_id"]):
            continue
        rows.append({
            "organization_id": m["organization_id"],
            "user_id": m["user_id"],
            "role": m["role"],
            "is_active": True,
        })
    if not rows:
        print("→ Memberships exist, skipping")
        return
    async with AsyncSessionLocal() as session:
        session.add_all(OrgMembership(**r) for r in rows)
        await session.commit()
    print(f"✓ {len(rows)} org membership(s) created")


async def seed_dlp_rules():
    """Seed DLP rules (idempotent via name unique enforcement)."""
    existing = 0
    async with AsyncSessionLocal() as session:
        for rule in DEFAULT_DLP_RULES:
            stmt = select(DlpRule).where(DlpRule.name == rule["name"])
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                existing += 1
                continue
            session.add(DlpRule(
                name=rule["name"],
                description=rule["description"],
                rule_type=rule["rule_type"],
                pattern=rule["pattern"],
                action=rule["action"],
                severity=rule["severity"],
                is_active=True,
            ))
        await session.commit()
    if existing == len(DEFAULT_DLP_RULES):
        print("→ DLP rules exist, skipping")
    else:
        print(f"✓ {len(DEFAULT_DLP_RULES) - existing} DLP rule(s) created")


async def seed_provider_policies():
    """Enable NVIDIA by default; leave Gemini as disabled (opt-in)."""
    if await row_exists(ProviderPolicy, organization_id=ORG_ID, provider_name="nvidia"):
        print("→ Provider policies exist, skipping")
        return
    policies = [
        ProviderPolicy(
            organization_id=ORG_ID,
            provider_name="nvidia",
            is_enabled=True,
            allow_reasoning=True,
        ),
        ProviderPolicy(
            organization_id=ORG_ID,
            provider_name="gemini",
            is_enabled=False,
            allow_reasoning=False,
        ),
    ]
    async with AsyncSessionLocal() as session:
        session.add_all(policies)
        await session.commit()
    print("✓ Provider policies created")


async def seed_model_policies():
    if await row_exists(ModelPolicy, organization_id=ORG_ID, provider_name="nvidia"):
        print("→ Model policies exist, skipping")
        return
    policies = []
    for model_name, cost_in, cost_out in MODEL_PRICING:
        policies.append(ModelPolicy(
            organization_id=ORG_ID,
            provider_name="nvidia",
            model_name=model_name,
            is_enabled=True,
            cost_per_1k_input=cost_in,
            cost_per_1k_output=cost_out,
        ))
    async with AsyncSessionLocal() as session:
        session.add_all(policies)
        await session.commit()
    print("✓ Model policies created")


async def seed_retention_policies():
    if await row_exists(RetentionPolicy, organization_id=ORG_ID, data_type="conversations"):
        print("→ Retention policies exist, skipping")
        return
    policies = []
    for data_type, soft_days, hard_days in RETENTION_CONFIGS:
        policies.append(RetentionPolicy(
            organization_id=ORG_ID,
            data_type=data_type,
            soft_delete_after_days=soft_days,
            hard_delete_after_days=hard_days,
            is_active=True,
        ))
    async with AsyncSessionLocal() as session:
        session.add_all(policies)
        await session.commit()
    print("✓ Retention policies created")


async def seed_sample_conversation():
    if await row_exists(Conversation, id=CONV_ID):
        print("→ Sample conversation exists, skipping")
        return
    async with AsyncSessionLocal() as session:
        conv = Conversation(
            id=CONV_ID,
            user_id=ADMIN_ID,
            organization_id=ORG_ID,
            title="Hello! 👋 Welcome to Dushman AI",
        )
        session.add(conv)
        await session.flush()

        messages = [
            Message(
                conversation_id=CONV_ID,
                role="user",
                content="Hello! What can you do? 🚀",
                model_used=None,
                provider_used=None,
            ),
            Message(
                conversation_id=CONV_ID,
                role="assistant",
                content=(
                    "Hi there! 👋 I'm Dushman AI, a multi-model AI assistant.\n\n"
                    "I can help you with:\n"
                    "- **Code generation & review** 💻\n"
                    "- **Document drafting** 📝\n"
                    "- **Data analysis & insights** 📊\n"
                    "- **Creative writing & brainstorming** 🎨\n"
                    "- **Research & summarization** 🔍\n\n"
                    "I support **streaming responses**, multiple AI models, "
                    "and persistent conversation history. What would you like to explore?"
                ),
                model_used="meta/llama-3.1-70b-instruct",
                provider_used="nvidia",
            ),
            Message(
                conversation_id=CONV_ID,
                role="user",
                content="Show me some Python code for a FastAPI endpoint!",
                model_used=None,
                provider_used=None,
            ),
            Message(
                conversation_id=CONV_ID,
                role="assistant",
                content=(
                    "Here's a simple FastAPI endpoint example:\n\n"
                    "```python\n"
                    "from fastapi import FastAPI, HTTPException\n"
                    "from pydantic import BaseModel\n\n"
                    "app = FastAPI(title=\"My API\")\n\n\n"
                    "class Item(BaseModel):\n"
                    "    name: str\n"
                    "    price: float\n"
                    "    in_stock: bool = True\n\n\n"
                    "@app.get(\"/\")\n"
                    "async def root():\n"
                    "    return {\"message\": \"Hello World\"}\n\n\n"
                    "@app.post(\"/items\")\n"
                    "async def create_item(item: Item):\n"
                    "    if item.price < 0:\n"
                    "        raise HTTPException(status_code=400, detail=\"Price must be positive\")\n"
                    "    return {\"id\": 1, **item.model_dump()}\n"
                    "```\n\n"
                    "This creates a simple API with:\n"
                    "- A root health-check endpoint **GET /**\n"
                    "- A typed item creation endpoint **POST /items**\n"
                    "- Input validation using Pydantic\n"
                    "- Error handling with HTTPException"
                ),
                model_used="meta/llama-3.1-70b-instruct",
                provider_used="nvidia",
            ),
        ]
        session.add_all(messages)
        await session.commit()
    print("✓ Sample conversation + 4 messages created")


async def seed_sample_usage():
    """Insert a few usage records for analytics visibility."""
    if await row_exists(UsageEvent, user_id=ADMIN_ID):
        print("→ Usage events exist, skipping")
        return

    today = date.today()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)

    usage_rows = [
        {"user_id": ADMIN_ID,  "provider": "nvidia", "model": "meta/llama-3.1-70b-instruct",      "day": day_before, "in": 250, "out": 800},
        {"user_id": USER_ID,   "provider": "nvidia", "model": "meta/llama-3-8b-instruct",          "day": yesterday,  "in": 120, "out": 340},
        {"user_id": MANAGER_ID,"provider": "nvidia", "model": "nvidia/llama-3.1-nemotron-70b-instruct","day": yesterday,"in": 400, "out": 1200},
        {"user_id": ADMIN_ID,  "provider": "nvidia", "model": "meta/llama-3.1-70b-instruct",      "day": today,      "in": 180, "out": 500},
        {"user_id": USER_ID,   "provider": "nvidia", "model": "meta/llama-3-8b-instruct",          "day": today,      "in": 90,  "out": 210},
    ]

    async with AsyncSessionLocal() as session:
        for r in usage_rows:
            total_tokens = r["in"] + r["out"]
            cost = round((r["in"] / 1000) * 0.00090 + (r["out"] / 1000) * 0.00090, 6)

            event = UsageEvent(
                user_id=r["user_id"],
                organization_id=ORG_ID,
                conversation_id=CONV_ID,
                provider_name=r["provider"],
                model_name=r["model"],
                input_tokens=r["in"],
                output_tokens=r["out"],
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=1200,
                stream_duration_ms=3500,
                retry_count=0,
                status="success",
                meta_data={"test_seed": True},
            )
            session.add(event)

            # Daily aggregate
            stmt = pg_insert(UsageDailyAggregate).values(
                organization_id=ORG_ID,
                user_id=r["user_id"],
                usage_date=r["day"],
                provider_name=r["provider"],
                model_name=r["model"],
                input_tokens=r["in"],
                output_tokens=r["out"],
                total_tokens=total_tokens,
                cost_usd=cost,
                request_count=1,
                error_count=0,
            ).on_conflict_do_update(
                index_elements=["organization_id", "user_id", "usage_date", "provider_name", "model_name"],
                set_={
                    "input_tokens": UsageDailyAggregate.input_tokens + r["in"],
                    "output_tokens": UsageDailyAggregate.output_tokens + r["out"],
                    "total_tokens": UsageDailyAggregate.total_tokens + total_tokens,
                    "cost_usd": UsageDailyAggregate.cost_usd + cost,
                    "request_count": UsageDailyAggregate.request_count + 1,
                },
            )
            await session.execute(stmt)

        await session.commit()
    print("✓ Sample usage events + aggregates created")


async def seed_sample_audit_logs():
    if await row_exists(AuditLog, event_type="signup"):
        print("→ Audit logs exist, skipping")
        return

    logs = [
        AuditLog(
            user_id=ADMIN_ID,
            organization_id=ORG_ID,
            event_type="signup",
            status="success",
            ip_address="127.0.0.1",
            user_agent="seed-script",
        ),
        AuditLog(
            user_id=ADMIN_ID,
            organization_id=ORG_ID,
            event_type="login",
            status="success",
            ip_address="127.0.0.1",
            user_agent="seed-script",
        ),
        AuditLog(
            user_id=ADMIN_ID,
            organization_id=ORG_ID,
            conversation_id=CONV_ID,
            event_type="message_submitted",
            status="success",
            provider_name="nvidia",
            model_name="meta/llama-3.1-70b-instruct",
            input_tokens=250,
            output_tokens=800,
            latency_ms=3200,
        ),
    ]
    async with AsyncSessionLocal() as session:
        session.add_all(logs)
        await session.commit()
    print("✓ Sample audit logs created")


async def verify_seed():
    """Run basic sanity checks and print a summary."""
    checks = []
    async with AsyncSessionLocal() as session:
        org_count   = (await session.execute(select(func.count()).select_from(Organization))).scalar()
        user_count  = (await session.execute(select(func.count()).select_from(User))).scalar()
        dlp_count   = (await session.execute(select(func.count()).select_from(DlpRule))).scalar()
        policy_count= (await session.execute(select(func.count()).select_from(ModelPolicy))).scalar()
        retention_c = (await session.execute(select(func.count()).select_from(RetentionPolicy))).scalar()
        conv_count  = (await session.execute(select(func.count()).select_from(Conversation))).scalar()
        msg_count   = (await session.execute(select(func.count()).select_from(Message))).scalar()
        usage_c     = (await session.execute(select(func.count()).select_from(UsageEvent))).scalar()
        audit_c     = (await session.execute(select(func.count()).select_from(AuditLog))).scalar()

    print("\n" + "=" * 52)
    print("  ✅  SEED VERIFICATION SUMMARY")
    print("=" * 52)
    print(f"  Organizations        {org_count:>3}")
    print(f"  Users                {user_count:>3}")
    print(f"  DLP Rules            {dlp_count:>3}")
    print(f"  Model Policies       {policy_count:>3}")
    print(f"  Retention Policies   {retention_c:>3}")
    print(f"  Conversations        {conv_count:>3}")
    print(f"  Messages             {msg_count:>3}")
    print(f"  Usage Events         {usage_c:>3}")
    print(f"  Audit Logs           {audit_c:>3}")
    print("=" * 52)

    if all([org_count, user_count, dlp_count, policy_count, conv_count, msg_count]):
        print("\n✅ Seed completed successfully! 🎉")
        print()
        print("  Login credentials:")
        print("    admin@dushman.ai  /  Admin@123   (super_admin)")
        print("    manager@dushman.ai / Manager@123  (manager)")
        print("    user@dushman.ai   /  User@123    (employee)")
    else:
        print("\n⚠️  Some seed data may be missing — review the counts above.")


# ── Main ─────────────────────────────────────────────────────────

async def main():
    print("🌱 Dushman AI — Database Seed\n")

    # 1. Ensure all models are registered on metadata
    from app.db import models as _models  # noqa: F401

    # 2. Create governance schema, all tables, and immutable triggers
    print("\nInitializing database schema (tables + immutable triggers)...")
    from app.core.database import init_db
    await init_db()
    print("✓ Schema + triggers created\n")

    # 3. Seed all data
    try:
        await seed_default_organization()
        await seed_users()
        await seed_org_memberships()
        await seed_dlp_rules()
        await seed_provider_policies()
        await seed_model_policies()
        await seed_retention_policies()
        await seed_sample_conversation()
        await seed_sample_usage()
        await seed_sample_audit_logs()

        # 4. Verify
        await verify_seed()
    finally:
        # 5. Cleanup — ensures engine is disposed even on failure
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
