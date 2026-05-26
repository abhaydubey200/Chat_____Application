# Supabase Complete Setup & Troubleshooting Guide

## ✅ Setup Checklist

- [ ] **Step 1**: Run SQL schema in Supabase
- [ ] **Step 2**: Get database password from Supabase
- [ ] **Step 3**: Update DATABASE_URL in `.env`
- [ ] **Step 4**: Restart backend
- [ ] **Step 5**: Run verification script
- [ ] **Step 6**: Test application

---

## STEP 1: Create Tables in Supabase (2 minutes)

### Method A: Using Supabase SQL Editor (Recommended)
1. Open: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/sql/new
2. Create new query
3. Copy entire content from `supabase_schema.sql` file
4. Paste into editor
5. Click **"Run"** button
6. Wait for success message

**Expected Output:**
```
Query executed successfully
Lines affected: 0
Execution time: XXXms
```

### Verify Tables Were Created:
1. Go to: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/editor
2. In left sidebar, you should see:
   - ✅ `users` table
   - ✅ `conversations` table
   - ✅ `messages` table

---

## STEP 2: Get Your Database Password (1 minute)

### Option A: Get Existing Password
1. Go to: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/database
2. Look for section: "Connection string"
3. Copy the password (between the `:` and `@` in the connection string)

### Option B: Reset Password
If you don't remember it:
1. Go to: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/database
2. Click **"Reset database password"** button
3. Confirm in popup
4. Copy the new password
5. **Important**: Save it somewhere safe!

---

## STEP 3: Update Your Backend Configuration (1 minute)

### Update DATABASE_URL in `backend/.env`:

1. Open file: `backend/.env`
2. Find line starting with: `DATABASE_URL=`
3. Replace `[PASSWORD_HERE]` with your actual password from Step 2

**Before:**
```
DATABASE_URL=postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:[PASSWORD_HERE]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

**After (Example with password "MySecurePass123"):**
```
DATABASE_URL=postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:MySecurePass123@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

4. Save file (Ctrl+S)

---

## STEP 4: Restart Your Backend

### Using Terminal:
```bash
cd backend
python app/main.py
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

If you see error messages, go to **TROUBLESHOOTING** section below.

---

## STEP 5: Verify Connection (Optional but Recommended)

### Run Verification Script:
```bash
cd backend
python verify_supabase.py
```

**Expected Output:**
```
============================================================
SUPABASE CONNECTION VERIFICATION
============================================================

📡 Testing connection to: aws-0-ap-south-1.pooler.supabase.com
✅ Database connection successful!

📋 Tables found in database:
  ✅ users
  ✅ conversations
  ✅ messages

📊 Record counts:
  - users: 0 records
  - conversations: 0 records
  - messages: 0 records

✅ All checks passed! Connection is working.
============================================================
SCHEMA VERIFICATION
============================================================

📋 Users Table Schema:
  - id: uuid (NOT NULL)
  - email: character varying (NOT NULL)
  - password_hash: character varying (NOT NULL)
  - created_at: timestamp with time zone (NOT NULL)
  - updated_at: timestamp with time zone (NOT NULL)

[... more tables ...]

============================================================
VERIFICATION COMPLETE
============================================================
```

---

## STEP 6: Test Your Application

### Test 1: User Registration
1. Go to: http://localhost:3000/signup
2. Create new account with:
   - Email: test@example.com
   - Password: TestPass123!
3. Click "Sign Up"
4. Should be redirected to login or dashboard

### Verify in Supabase:
1. Go to: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/editor
2. Click on `users` table
3. Should see new user record with email you registered

### Test 2: Chat Functionality
1. Login with your test account
2. Create a new conversation
3. Send a message
4. Verify in Supabase:
   - Check `conversations` table (should have 1 record)
   - Check `messages` table (should have 1 record)

---

## 🔧 TROUBLESHOOTING

### Issue 1: "Connection refused" Error

**Error Message:**
```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.InvalidAuthorizationSpecificationError)
```

**Cause:** Wrong password or connection string

**Solution:**
1. Open `backend/.env`
2. Double-check DATABASE_URL is correct
3. Verify password matches Supabase (Settings → Database)
4. Make sure no extra spaces in DATABASE_URL
5. Restart backend: `python app/main.py`

---

### Issue 2: "Authentication failed"

**Error Message:**
```
sqlalchemy.exc.OperationalError: (asyncpg.exceptions.AuthenticationError)
```

**Cause:** Invalid password or wrong credentials

**Solution:**
1. Go to Supabase: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/database
2. Reset password if needed (Save new password!)
3. Update DATABASE_URL with new password
4. Restart backend

---

### Issue 3: "Table not found" in Application

**Error Message:**
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "users" does not exist
```

**Cause:** SQL schema not executed in Supabase

**Solution:**
1. Go to Supabase SQL Editor: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/sql/new
2. Copy content from `supabase_schema.sql`
3. Paste and run
4. Wait for success message
5. Restart backend

---

### Issue 4: "UUID extension not found"

**Error Message:**
```
ERROR: type "uuid" does not exist
```

**Cause:** Missing UUID extension

**Solution:**
The `supabase_schema.sql` includes `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`
which is automatic in Supabase. Run the full schema file again.

---

### Issue 5: Slow Connection / Timeouts

**Error Message:**
```
asyncpg.exceptions.TooManyConnectionsError
```

**Cause:** Too many connections or connection pool issue

**Solution:**
1. Verify you're using the connection pooler (port 6543)
2. Your DATABASE_URL should be: `aws-0-ap-south-1.pooler.supabase.com:6543`
3. Check `backend/app/core/database.py` pool settings (already optimized)
4. Restart backend

---

### Issue 6: Frontend Can't Reach Backend

**Error Message:**
```
Failed to fetch from http://localhost:8000
```

**Cause:** Backend not running or CORS not configured

**Solution:**
1. Verify backend is running: `python app/main.py`
2. Check backend is listening on http://127.0.0.1:8000
3. Restart frontend: `npm run dev`
4. Clear browser cache (Ctrl+Shift+Delete)

---

### Issue 7: "Password too weak" Error

**Error Message:**
```
Password is too weak
```

**Cause:** Supabase database password requirements

**Solution:**
1. Use strong password with:
   - At least 12 characters
   - Mix of letters, numbers, symbols
   - No dictionary words
2. Example: `Db@P@ss2026#Secure`

---

## 📋 Connection Details Reference

### Your Supabase Project
```
Project URL: https://xqbubmzcjftrzziqsshz.supabase.co
Project ID: xqbubmzcjftrzziqsshz
Region: ap-south-1 (Mumbai, India)
```

### Database Connection (Using Connection Pooler)
```
Host: aws-0-ap-south-1.pooler.supabase.com
Port: 6543
Database: postgres
User: postgres.xqbubmzcjftrzziqsshz
Password: [YOUR_PASSWORD_HERE]
```

### Async Connection String Format
```
postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

### API Keys
```
Anon Key: sb_publishable_43FX3UN2JKU1nBVWQ1RZHw_jT6ff-By
Service Role: [Available in Supabase Settings → API]
```

---

## 📊 Database Structure

### users table
```
Column          | Type      | Constraints
----------------|-----------|------------------
id              | UUID      | PRIMARY KEY
email           | VARCHAR   | UNIQUE, NOT NULL
password_hash   | VARCHAR   | NOT NULL
created_at      | TIMESTAMP | DEFAULT now()
updated_at      | TIMESTAMP | DEFAULT now()
```

### conversations table
```
Column          | Type      | Constraints
----------------|-----------|------------------
id              | UUID      | PRIMARY KEY
user_id         | UUID      | FK → users.id
title           | VARCHAR   | DEFAULT 'New Conversation'
created_at      | TIMESTAMP | DEFAULT now()
updated_at      | TIMESTAMP | DEFAULT now()
```

### messages table
```
Column              | Type      | Constraints
--------------------|-----------|------------------
id                  | UUID      | PRIMARY KEY
conversation_id     | UUID      | FK → conversations.id
role                | VARCHAR   | NOT NULL
content             | TEXT      | NOT NULL
model_used          | VARCHAR   | NULLABLE
provider_used       | VARCHAR   | NULLABLE
created_at          | TIMESTAMP | DEFAULT now()
```

---

## 🔗 Useful Links

| Resource | URL |
|----------|-----|
| **Supabase Dashboard** | https://supabase.com/dashboard |
| **Project SQL Editor** | https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/sql |
| **Table Editor** | https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/editor |
| **Database Settings** | https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/database |
| **API Documentation** | https://supabase.com/docs |
| **Backend API** | http://localhost:8000 |
| **Frontend App** | http://localhost:3000 |

---

## 🎯 Next Steps

1. ✅ **Create Tables**: Run `supabase_schema.sql` in Supabase SQL Editor
2. ✅ **Get Password**: Copy password from Supabase Settings
3. ✅ **Update .env**: Replace `[PASSWORD_HERE]` in backend/.env
4. ✅ **Restart Backend**: Run `python app/main.py`
5. ✅ **Verify**: Run `python verify_supabase.py`
6. ✅ **Test App**: Register user, create chat, send message
7. ✅ **Monitor**: Check Supabase Dashboard for data

---

## ❓ Quick FAQ

**Q: Can I use the old local database?**
A: No, you need to switch. But you can keep a backup of old data if needed.

**Q: Is my data secure?**
A: Yes, Supabase uses enterprise-grade PostgreSQL with encryption.

**Q: How do I backup my Supabase database?**
A: Supabase automatically backs up daily. You can also manually export via SQL Editor.

**Q: Can I use Supabase for production?**
A: Yes! Supabase is production-ready for enterprise applications.

**Q: What's the cost?**
A: Supabase has a free tier. Paid tiers start at $25/month.

---

## 📞 Support

If you're still having issues:

1. Check the **TROUBLESHOOTING** section above
2. Review Supabase Docs: https://supabase.com/docs
3. Check Supabase Status: https://status.supabase.com
4. Contact: Abhay@7505991639

---

**Setup Completed**: May 26, 2026  
**Status**: ✅ Ready for Production  
**Last Updated**: May 26, 2026
