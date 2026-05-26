# Supabase Migration Setup Guide

## Overview
This guide walks you through migrating your Chat Application from local PostgreSQL to Supabase.

---

## Step 1: Get Your Supabase Connection Details

Your Supabase Project Reference ID: **xqbubmzcjftrzziqsshz**

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/database)
2. Click on **Settings** → **Database**
3. Copy the connection string details

### Required Information:
- **Database Password** - You should have set this when creating the project
  - If you forgot it, go to Settings → Database and reset it
- **Connection String** - Will look like:
  ```
  postgresql://postgres.xqbubmzcjftrzziqsshz:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
  ```

---

## Step 2: Create Tables on Supabase

1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz) 
2. Navigate to **SQL Editor** (left sidebar)
3. Click **New Query**
4. Open and copy the entire content from: `supabase_schema.sql`
5. Paste it into the SQL editor
6. Click **Run** button
7. Verify all tables are created (you should see: `users`, `conversations`, `messages`)

### Or Create Individual Tables:

You can also paste each table creation separately if needed.

---

## Step 3: Update Your Backend Configuration

### Update the DATABASE_URL in `.env`:

1. Open `backend/.env`
2. Update the `DATABASE_URL` with your Supabase connection string:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:[YOUR_PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```
   - Replace `[YOUR_PASSWORD]` with your actual database password

### Optional: Add Supabase API Keys:

```env
SUPABASE_URL=https://xqbubmzcjftrzziqsshz.supabase.co
SUPABASE_ANON_KEY=sb_publishable_43FX3UN2JKU1nBVWQ1RZHw_jT6ff-By
SUPABASE_SERVICE_ROLE_KEY=[Get from Settings → API → Service role secret]
```

---

## Step 4: Update Backend Dependencies

No changes needed! Your current dependencies already support Supabase:
- ✅ SQLAlchemy (ORM)
- ✅ asyncpg (PostgreSQL driver)
- ✅ python-dotenv (environment variables)

---

## Step 5: Restart Your Application

### Backend:
```bash
cd backend
python -m pip install -r requirements.txt  # if needed
python app/main.py
```

### Frontend:
```bash
cd frontend
npm run dev
```

---

## Step 6: Testing

1. **Test Backend Connection:**
   ```bash
   cd backend
   python verify_backend.py
   ```

2. **Test User Registration:**
   - Go to frontend signup page
   - Create a new account
   - Check if data appears in Supabase Dashboard → Table Editor → `users`

3. **Test Chat Functionality:**
   - Create a new conversation
   - Send messages
   - Verify data in Supabase Dashboard → Table Editor → `conversations` and `messages`

---

## Supabase Connection Details

### Project URL
```
https://xqbubmzcjftrzziqsshz.supabase.co
```

### Database Region
```
ap-south-1 (Mumbai, India)
```

### Connection Pool
Your connection string already uses the **Connection Pooler** for better performance:
- Host: `aws-0-ap-south-1.pooler.supabase.com:6543`

---

## Common Issues & Solutions

### Issue 1: "Connection refused" Error
- **Cause:** Wrong password or host
- **Fix:** Verify your DATABASE_URL is correct. Check the password in Supabase Dashboard

### Issue 2: "Authentication failed" Error
- **Cause:** Invalid API key
- **Fix:** Double-check SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY

### Issue 3: Table Not Found Error
- **Cause:** SQL schema not executed
- **Fix:** Run the `supabase_schema.sql` file again in SQL Editor

### Issue 4: UUID Extension Not Available
- **Cause:** Extension not created
- **Fix:** The SQL file includes `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` which is automatic

---

## Database Specifications

### Tables Created:

#### users
```
- id (UUID, Primary Key)
- email (VARCHAR, UNIQUE)
- password_hash (VARCHAR)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

#### conversations
```
- id (UUID, Primary Key)
- user_id (UUID, Foreign Key → users.id)
- title (VARCHAR)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

#### messages
```
- id (UUID, Primary Key)
- conversation_id (UUID, Foreign Key → conversations.id)
- role (VARCHAR: 'user' or 'assistant')
- content (TEXT)
- model_used (VARCHAR)
- provider_used (VARCHAR)
- created_at (TIMESTAMP)
```

### Indexes Created:
- `idx_users_email` - For fast email lookups
- `idx_conversations_user_id` - For fast user conversation queries
- `idx_conversations_created_at` - For sorting conversations
- `idx_messages_conversation_id` - For fast message queries
- `idx_messages_created_at` - For sorting messages

---

## Next Steps

1. ✅ Copy the SQL schema file
2. ✅ Execute SQL on Supabase
3. ✅ Update `.env` with connection string
4. ✅ Restart backend
5. ✅ Test functionality
6. ✅ Monitor Supabase dashboard for data

---

## Support

If you encounter any issues:
1. Check Supabase Dashboard → Logs
2. Check backend logs for detailed error messages
3. Verify DATABASE_URL format is correct
4. Ensure all tables are created in Supabase

---

**Migration Date:** May 26, 2026  
**Project Reference:** xqbubmzcjftrzziqsshz  
**Status:** Ready for deployment
