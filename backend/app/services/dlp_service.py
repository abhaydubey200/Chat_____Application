import re
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select, func
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.observability import get_request_context, get_logger
from app.core.time import utc_now
from app.db.models import DlpRule, DlpEvent

logger = get_logger(__name__)

ACTION_PRIORITY = {
    "allow": 0,
    "warn": 1,
    "escalate": 2,
    "block": 3,
}

DEFAULT_RULES = [
    {
        "name": "JWT token",
        "description": "Detect JWT token patterns",
        "rule_type": "regex",
        "pattern": r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}",
        "action": "block",
        "severity": "high",
    },
    {
        "name": "API key assignment",
        "description": "Detect API key like assignments",
        "rule_type": "regex",
        "pattern": r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[\"']?([a-zA-Z0-9_\-\.]{12,})",
        "action": "block",
        "severity": "high",
    },
    {
        "name": "SSH private key",
        "description": "Detect private key blocks",
        "rule_type": "regex",
        "pattern": r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "Database URL",
        "description": "Detect database connection strings",
        "rule_type": "regex",
        "pattern": r"(?i)postgres(?:ql)?://[^\s]+",
        "action": "block",
        "severity": "high",
    },
    {
        "name": "Credit card",
        "description": "Detect potential credit card numbers",
        "rule_type": "regex",
        "pattern": r"\b(?:\d[ -]*?){13,19}\b",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "Aadhaar",
        "description": "Detect Aadhaar numbers",
        "rule_type": "regex",
        "pattern": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "PAN",
        "description": "Detect PAN identifiers",
        "rule_type": "regex",
        "pattern": r"\b[A-Z]{5}\d{4}[A-Z]\b",
        "action": "block",
        "severity": "critical",
    },
    {
        "name": "Internal URL",
        "description": "Detect internal/private URLs",
        "rule_type": "regex",
        "pattern": r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)[^\s]*",
        "action": "warn",
        "severity": "medium",
    },
    {
        "name": "Confidential keywords",
        "description": "Detect confidentiality indicators",
        "rule_type": "keyword",
        "pattern": "confidential,internal use only,do not share,private,secret",
        "action": "warn",
        "severity": "medium",
    },
]

@dataclass
class DlpMatch:
    rule_id: uuid.UUID | None
    rule_name: str
    action: str
    severity: str
    matches: list[str]

@dataclass
class DlpResult:
    action: str
    matches: list[DlpMatch]
    redacted_text: str

class DlpService:
    _cached_rules: list[DlpRule] | None = None
    _cache_expires_at: datetime | None = None

    @staticmethod
    async def _load_rules() -> list[DlpRule]:
        if DlpService._cached_rules and DlpService._cache_expires_at:
            if utc_now() < DlpService._cache_expires_at:
                return DlpService._cached_rules

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(DlpRule).where(DlpRule.is_active.is_(True)))
            rules = list(result.scalars().all())
            if not rules:
                await DlpService._seed_default_rules(session)
                result = await session.execute(select(DlpRule).where(DlpRule.is_active.is_(True)))
                rules = list(result.scalars().all())

        DlpService._cached_rules = rules
        DlpService._cache_expires_at = utc_now() + timedelta(seconds=300)
        return rules

    @staticmethod
    async def _seed_default_rules(session) -> None:
        count = await session.execute(select(func.count()).select_from(DlpRule))
        if count.scalar() and count.scalar() > 0:
            return
        for rule in DEFAULT_RULES:
            session.add(DlpRule(**rule))
        await session.commit()

    @staticmethod
    def _shannon_entropy(value: str) -> float:
        if not value:
            return 0.0
        freq = {}
        for ch in value:
            freq[ch] = freq.get(ch, 0) + 1
        entropy = 0.0
        for count in freq.values():
            p = count / len(value)
            entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def _entropy_matches(text: str) -> list[str]:
        tokens = re.split(r"[^A-Za-z0-9_\-+=]", text)
        matches = []
        for token in tokens:
            if len(token) < settings.DLP_MIN_SECRET_LENGTH:
                continue
            entropy = DlpService._shannon_entropy(token)
            if entropy >= settings.DLP_ENTROPY_THRESHOLD:
                matches.append(token)
            if len(matches) >= settings.DLP_MAX_MATCHES:
                break
        return matches

    @staticmethod
    def _apply_redactions(text: str, patterns: list[str]) -> str:
        redacted = text
        for pattern in patterns:
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
        return redacted

    @staticmethod
    async def scan_prompt(prompt: str) -> DlpResult:
        rules = await DlpService._load_rules()
        matches: list[DlpMatch] = []
        redaction_patterns: list[str] = []

        for rule in rules:
            if rule.rule_type == "regex":
                found = re.findall(rule.pattern, prompt, flags=re.IGNORECASE)
                if found:
                    matches.append(DlpMatch(rule.id, rule.name, rule.action, rule.severity, [str(f) for f in found]))
                    redaction_patterns.append(rule.pattern)
            elif rule.rule_type == "keyword":
                keywords = [k.strip() for k in rule.pattern.split(",") if k.strip()]
                found = [k for k in keywords if k.lower() in prompt.lower()]
                if found:
                    matches.append(DlpMatch(rule.id, rule.name, rule.action, rule.severity, found))
                    redaction_patterns.extend([re.escape(k) for k in found])
            elif rule.rule_type == "entropy":
                found = DlpService._entropy_matches(prompt)
                if found:
                    matches.append(DlpMatch(rule.id, rule.name, rule.action, rule.severity, found))
                    redaction_patterns.extend([re.escape(f) for f in found])

        entropy_matches = DlpService._entropy_matches(prompt)
        if entropy_matches:
            matches.append(DlpMatch(None, "High entropy secret", "warn", "medium", entropy_matches))
            redaction_patterns.extend([re.escape(f) for f in entropy_matches])

        action = settings.DLP_DEFAULT_ACTION
        if matches:
            action = max((m.action for m in matches), key=lambda a: ACTION_PRIORITY.get(a, 0))

        redacted_text = DlpService._apply_redactions(prompt, redaction_patterns)
        return DlpResult(action=action, matches=matches, redacted_text=redacted_text)

    @staticmethod
    async def record_event(
        result: DlpResult,
        user_id: uuid.UUID | None,
        organization_id: uuid.UUID | None,
        conversation_id: uuid.UUID | None,
    ) -> None:
        ctx = get_request_context()
        match_count = sum(len(match.matches) for match in result.matches)
        async with AsyncSessionLocal() as session:
            event = DlpEvent(
                request_id=ctx.request_id if ctx else None,
                session_id=ctx.session_id if ctx else None,
                user_id=user_id,
                organization_id=organization_id,
                conversation_id=conversation_id,
                action=result.action,
                match_count=match_count,
                redacted_excerpt=result.redacted_text[:300] if result.redacted_text else None,
                meta_data={
                    "matches": [
                        {
                            "rule_id": str(match.rule_id) if match.rule_id else None,
                            "rule_name": match.rule_name,
                            "action": match.action,
                            "severity": match.severity,
                            "match_count": len(match.matches),
                        }
                        for match in result.matches
                    ]
                },
            )
            session.add(event)
            await session.commit()
