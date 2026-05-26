# Supabase Migration - Quick Reference

## Your Supabase Credentials
```
Project URL: https://xqbubmzcjftrzziqsshz.supabase.co
Project ID: xqbubmzcjftrzziqsshz
Region: ap-south-1 (Mumbai)
Anon Key: sb_publishable_43FX3UN2JKU1nBVWQ1RZHw_jT6ff-By
```

---

## 5-Minute Quick Setup

### 1. Create Tables (2 minutes)
1. Go to: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/sql
2. Click "New Query"
3. Copy & paste content from: **`supabase_schema.sql`**
4. Click "Run"
5. ✅ Done!

### 2. Get Database Password (1 minute)
1. Go to: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/database
2. Look for: "Database password" (or click "Reset password" if needed)
3. Copy the password

### 3. Update .env (1 minute)
1. Open: `backend/.env`
2. Find: `DATABASE_URL=postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:[PASSWORD_HERE]@...`
3. Replace `[PASSWORD_HERE]` with your password from step 2
4. Save file

### 4. Restart Backend (1 minute)
```bash
cd backend
python app/main.py
```

---

## Files Created/Modified

| File | Purpose |
|------|---------|
| **`supabase_schema.sql`** | SQL schema - Run in Supabase |
| **`SUPABASE_SETUP_GUIDE.md`** | Detailed setup instructions |
| **`backend/.env`** | Updated with Supabase credentials |
| **`backend/verify_supabase.py`** | Verify connection script |

---

## Testing Your Setup

### Option 1: Using Verification Script
```bash
cd backend
python verify_supabase.py
```

Expected output:
```
✅ Database connection successful!
✅ users table
✅ conversations table
✅ messages table
```

### Option 2: Manual Testing
1. Signup at: http://localhost:3000/signup
2. Go to Supabase Dashboard → Table Editor
3. Check if new user appears in `users` table
4. Create a chat conversation
5. Check if it appears in `conversations` table

---

## Connection String Format

Your DATABASE_URL should look like:
```
postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

Where:
- `[PASSWORD]` = Your Supabase database password
- Don't change the host/port - it's optimized for connection pooling
- Protocol: `postgresql+asyncpg` (required for async)

---

## Important Notes

1. **Connection Pooler**: Your connection string uses Supabase's connection pooler (port 6543) for better performance
2. **UUID Extension**: Already enabled in SQL schema
3. **Indexes**: All optimized indexes are created automatically
4. **No Schema Conflicts**: Old local DB won't interfere (you can delete it later)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Authentication failed" | Check password in Supabase Settings → Database |
| "Connection refused" | Verify host and port in DATABASE_URL |
| "Table not found" | Run `supabase_schema.sql` in Supabase SQL Editor |
| "UUID not found" | Extension created automatically in schema file |
| Slow connection | Using connection pooler (normal, optimized for pooling) |

---

## Next Steps After Setup

1. ✅ Verify connection with `verify_supabase.py`
2. ✅ Test user registration
3. ✅ Test chat functionality
4. ✅ Monitor Supabase Dashboard for data
5. ✅ Clean up old local database (if desired)

---

## Useful Supabase Dashboard Links

- **SQL Editor**: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/sql
- **Table Editor**: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/editor
- **Database Settings**: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/database
- **API Docs**: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/api

---

## Database Schema Summary

```
users
├── id (UUID) - Primary Key
├── email (VARCHAR) - Unique
├── password_hash (VARCHAR)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

conversations
├── id (UUID) - Primary Key
├── user_id (UUID) - Foreign Key → users.id
├── title (VARCHAR)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

messages
├── id (UUID) - Primary Key
├── conversation_id (UUID) - Foreign Key → conversations.id
├── role (VARCHAR)
├── content (TEXT)
├── model_used (VARCHAR)
├── provider_used (VARCHAR)
└── created_at (TIMESTAMP)
```

---

**Status**: ✅ Ready for deployment  
**Last Updated**: May 26, 2026  
**Support Contact**: Abhay@7505991639
