#!/usr/bin/env python3
"""
Supabase Connection Verification Script
Test your Supabase database connection and schema
"""

import asyncio
import os
from urllib.parse import urlsplit
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, inspect
from app.core.db_url import normalize_database_url, build_connect_args

# Load environment variables
load_dotenv()

RAW_DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL = normalize_database_url(RAW_DATABASE_URL) if RAW_DATABASE_URL else None
SUPABASE_SSL_NO_VERIFY = os.getenv("SUPABASE_SSL_NO_VERIFY", "").strip().lower() in {"1", "true", "yes"}


def format_db_target(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or "DATABASE"
    port = f":{parts.port}" if parts.port else ""
    db = parts.path.lstrip("/")
    return f"{host}{port}/{db}" if db else f"{host}{port}"

async def verify_connection():
    """Verify database connection"""
    print("=" * 60)
    print("SUPABASE CONNECTION VERIFICATION")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL not found in .env file")
        return False
    
    print(f"\n📡 Testing connection to: {format_db_target(DATABASE_URL)}")
    
    try:
        # Create async engine
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            connect_args=build_connect_args(
                DATABASE_URL,
                {"timeout": 10},
                disable_ssl_verify=SUPABASE_SSL_NO_VERIFY,
            ),
        )
        
        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            
        # Check tables
        async with engine.begin() as conn:
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            
            print("\n📋 Tables found in database:")
            required_tables = ["users", "conversations", "messages"]
            
            for table in required_tables:
                if table in tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} (MISSING - Run supabase_schema.sql)")
            
            # Count records in each table
            print("\n📊 Record counts:")
            for table in required_tables:
                if table in tables:
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"  - {table}: {count} records")
        
        await engine.dispose()
        print("\n✅ All checks passed! Connection is working.")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Verify DATABASE_URL in .env file")
        print("2. Check if password is correct (get from Supabase Dashboard)")
        print("3. Ensure tables are created (run supabase_schema.sql in Supabase SQL Editor)")
        print("4. Check your internet connection to Supabase")
        return False

async def verify_schema():
    """Verify database schema"""
    print("\n" + "=" * 60)
    print("SCHEMA VERIFICATION")
    print("=" * 60)
    
    try:
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            connect_args=build_connect_args(
                DATABASE_URL,
                disable_ssl_verify=SUPABASE_SSL_NO_VERIFY,
            ),
        )
        
        async with engine.begin() as conn:
            # Check users table
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """))
            
            print("\n📋 Users Table Schema:")
            columns = result.fetchall()
            if columns:
                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    print(f"  - {col[0]}: {col[1]} ({nullable})")
            else:
                print("  ❌ Table not found!")
            
            # Check conversations table
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'conversations'
                ORDER BY ordinal_position
            """))
            
            print("\n📋 Conversations Table Schema:")
            columns = result.fetchall()
            if columns:
                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    print(f"  - {col[0]}: {col[1]} ({nullable})")
            else:
                print("  ❌ Table not found!")
            
            # Check messages table
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'messages'
                ORDER BY ordinal_position
            """))
            
            print("\n📋 Messages Table Schema:")
            columns = result.fetchall()
            if columns:
                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    print(f"  - {col[0]}: {col[1]} ({nullable})")
            else:
                print("  ❌ Table not found!")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Schema verification failed: {str(e)}")

async def main():
    """Run all verifications"""
    connection_ok = await verify_connection()
    
    if connection_ok:
        await verify_schema()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
