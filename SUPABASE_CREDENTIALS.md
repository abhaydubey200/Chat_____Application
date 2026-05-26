# Supabase API Keys & Credentials Guide

## 🔑 Your API Keys

### Anon Key (Public)
```
sb_publishable_43FX3UN2JKU1nBVWQ1RZHw_jT6ff-By
```
**Where to use**: Frontend (safe to expose)

### Service Role Key (Secret)
```
Get from: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/api
```
**Where to use**: Backend (keep secret!)

---

## How to Get Service Role Key

1. Go to: https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/api
2. Look for section: "Project API keys"
3. You'll see:
   - **`anon` (public)** - Already have this
   - **`service_role` (secret)** - Copy this
4. Paste in `backend/.env`:
   ```
   SUPABASE_SERVICE_ROLE_KEY=sbp_xxxxxxxxxxxxxxxxxxxx
   ```

---

## 🔐 Database Credentials

### Connection String (For Backend)
```
postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

### Project URL (For Frontend)
```
https://xqbubmzcjftrzziqsshz.supabase.co
```

### Database Password
```
🔑 You set this when creating the project
📝 If forgotten: Settings → Database → Reset password
```

---

## .env Configuration

### Minimal Setup (Required)
```env
DATABASE_URL=postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

### Complete Setup (Optional)
```env
# Database Connection
DATABASE_URL=postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

# Supabase API
SUPABASE_URL=https://xqbubmzcjftrzziqsshz.supabase.co
SUPABASE_ANON_KEY=sb_publishable_43FX3UN2JKU1nBVWQ1RZHw_jT6ff-By
SUPABASE_SERVICE_ROLE_KEY=sbp_xxxxxxxxxxxxxxxxxxxx
```

---

## 🔗 Dashboard Links by Purpose

| What | Link |
|------|------|
| **Get API Keys** | https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/api |
| **Get DB Password** | https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/settings/database |
| **View Tables** | https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/editor |
| **SQL Editor** | https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/sql |
| **Logs** | https://supabase.com/dashboard/project/xqbubmzcjftrzziqsshz/logs |

---

## 🚨 Security Tips

1. **Never share Database URL** with password
2. **Keep Service Role Key secret** - don't expose to frontend
3. **Use Anon Key for frontend** - it's public by design
4. **Rotate keys regularly** - available in Settings → API
5. **Use different projects** for dev/staging/production

---

## Connection String Components

```
postgresql+asyncpg://user:password@host:port/database

Where:
- Protocol: postgresql+asyncpg (async PostgreSQL driver)
- User: postgres.xqbubmzcjftrzziqsshz
- Password: [Your database password]
- Host: aws-0-ap-south-1.pooler.supabase.com (connection pooler)
- Port: 6543 (connection pooler port)
- Database: postgres (default)
```

---

## Environment Variables Summary

```bash
# Required for Backend
DATABASE_URL=postgresql+asyncpg://postgres.xqbubmzcjftrzziqsshz:YOUR_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

# Optional for API calls from backend
SUPABASE_URL=https://xqbubmzcjftrzziqsshz.supabase.co
SUPABASE_ANON_KEY=sb_publishable_43FX3UN2JKU1nBVWQ1RZHw_jT6ff-By
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY

# Your existing keys (keep these)
JWT_SECRET=dushman-ai-super-secret-jwt-key-2026
NVIDIA_API_KEY=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
GEMINI_API_KEY=your-gemini-api-key-here
```

---

## Testing Credentials

### Test User (For Development)
```
Email: test@example.com
Password: TestPassword123!
```

Create this after setting up Supabase.

---

## Credentials Checklist

- [ ] Database password obtained
- [ ] DATABASE_URL updated in .env
- [ ] Anon Key saved
- [ ] Service Role Key saved (in .env)
- [ ] All environment variables verified
- [ ] Backend restarted after .env update

---

**Last Updated**: May 26, 2026  
**Status**: ✅ Credentials Guide Complete
