#!/usr/bin/env python3
"""
Environment Configuration Validator

This script validates all required environment variables are properly configured
before running the application. Run this before starting the app in production.

Usage:
    python validate_env.py
"""

import os
import sys
import re
from pathlib import Path
from urllib.parse import urlparse

def validate_jwt_secret(secret: str) -> tuple[bool, str]:
    """Validate JWT_SECRET is sufficiently strong."""
    if not secret:
        return False, "JWT_SECRET is not set"
    if len(secret) < 64:
        return False, f"JWT_SECRET must be at least 64 characters (currently {len(secret)})"
    if "change" in secret.lower() or "placeholder" in secret.lower():
        return False, "JWT_SECRET contains placeholder values"
    if secret.count('-') > 5:
        return False, "JWT_SECRET looks like a weak pattern"
    return True, "JWT_SECRET is properly configured"

def validate_database_url(url: str) -> tuple[bool, str]:
    """Validate DATABASE_URL format and accessibility."""
    if not url:
        return False, "DATABASE_URL is not set"
    
    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False, "DATABASE_URL missing hostname"
        if not parsed.database:
            return False, "DATABASE_URL missing database name"
        if "asyncpg" not in url and "asyncio" not in url:
            return False, "DATABASE_URL should use asyncpg driver for async support"
        return True, f"DATABASE_URL is valid ({parsed.hostname}:{parsed.database})"
    except Exception as e:
        return False, f"Invalid DATABASE_URL format: {e}"

def validate_cors_origins(origins: str, env: str) -> tuple[bool, str]:
    """Validate CORS_ORIGINS are properly configured."""
    if not origins:
        if env == "production":
            return False, "CORS_ORIGINS must be configured in production"
        return True, "CORS_ORIGINS not set (using defaults for development)"
    
    origin_list = [o.strip() for o in origins.split(",") if o.strip()]
    if not origin_list:
        if env == "production":
            return False, "CORS_ORIGINS is empty but required in production"
        return True, "CORS_ORIGINS is empty (using defaults)"
    
    for origin in origin_list:
        if not origin.startswith(("http://", "https://")):
            return False, f"Invalid origin format (must start with http:// or https://): {origin}"
        if " " in origin:
            return False, f"Origin contains spaces: {origin}"
    
    if env == "production":
        if any("localhost" in o or "127.0.0.1" in o for o in origin_list):
            return False, "Cannot use localhost origins in production"
    
    return True, f"CORS_ORIGINS properly configured ({len(origin_list)} origins)"

def validate_llm_provider(provider: str, api_key: str | None) -> tuple[bool, str]:
    """Validate LLM provider configuration."""
    if not provider:
        return False, "LLM_PROVIDER is not set"
    
    provider = provider.lower().strip()
    if provider not in {"nvidia", "gemini"}:
        return False, f"LLM_PROVIDER must be 'nvidia' or 'gemini', got: {provider}"
    
    if provider == "nvidia":
        if not api_key:
            return False, "NVIDIA_API_KEY must be set when LLM_PROVIDER=nvidia"
        if not api_key.startswith("nvapi-"):
            return False, "NVIDIA_API_KEY should start with 'nvapi-'"
        return True, "NVIDIA provider configured"
    
    elif provider == "gemini":
        if not api_key:
            return False, "GEMINI_API_KEY must be set when LLM_PROVIDER=gemini"
        return True, "Gemini provider configured"
    
    return False, "Unknown LLM provider"

def validate_redis(enabled: str, url: str | None) -> tuple[bool, str]:
    """Validate Redis configuration if enabled."""
    if enabled and enabled.lower() in {"true", "1", "yes"}:
        if not url:
            return False, "REDIS_URL must be set when REDIS_ENABLED=true"
        try:
            parsed = urlparse(url)
            if parsed.scheme != "redis":
                return False, f"Invalid Redis URL scheme (expected redis://): {parsed.scheme}://"
            return True, "Redis properly configured"
        except Exception as e:
            return False, f"Invalid REDIS_URL format: {e}"
    return True, "Redis not enabled (optional)"

def main():
    """Run all validation checks."""
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    checks = []
    passed = 0
    failed = 0
    
    # Get environment variables
    env = os.getenv("ENV", "development")
    jwt_secret = os.getenv("JWT_SECRET", "")
    db_url = os.getenv("DATABASE_URL", "")
    cors_origins = os.getenv("CORS_ORIGINS", "")
    llm_provider = os.getenv("LLM_PROVIDER", "")
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    redis_enabled = os.getenv("REDIS_ENABLED", "false")
    redis_url = os.getenv("REDIS_URL")
    
    print("\n" + "="*70)
    print(f"Environment Validation Report - {env.upper()} Mode")
    print("="*70 + "\n")
    
    # Run checks
    validators = [
        ("JWT_SECRET", lambda: validate_jwt_secret(jwt_secret)),
        ("DATABASE_URL", lambda: validate_database_url(db_url)),
        ("CORS_ORIGINS", lambda: validate_cors_origins(cors_origins, env)),
        ("LLM_PROVIDER", lambda: validate_llm_provider(llm_provider, nvidia_key or gemini_key)),
        ("Redis", lambda: validate_redis(redis_enabled, redis_url)),
    ]
    
    for check_name, validator in validators:
        try:
            is_valid, message = validator()
            status = "✓ PASS" if is_valid else "✗ FAIL"
            print(f"{status}: {check_name}")
            print(f"       {message}\n")
            
            if is_valid:
                passed += 1
            else:
                failed += 1
            checks.append((check_name, is_valid, message))
        except Exception as e:
            print(f"✗ ERROR: {check_name}")
            print(f"         {e}\n")
            failed += 1
            checks.append((check_name, False, str(e)))
    
    # Summary
    print("="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    if failed > 0:
        print("❌ Configuration validation FAILED")
        print("\nPlease fix the issues above before running the application in production.")
        return 1
    else:
        print("✅ All configuration checks PASSED")
        print("\nYour application is ready for deployment!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
