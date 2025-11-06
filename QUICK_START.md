# Quick Start - User Accounts with Supabase

## 🚀 Get Running in 5 Minutes

### Step 1: Get Service Role Key
1. Go to: https://supabase.com/dashboard/project/erjabdqbgancubnqwcdl/settings/api
2. Copy the **service_role** secret key (starts with `eyJ...`)

### Step 2: Backend Setup

```bash
cd poke-backend

# Install
uv sync

# Create .env
cat > .env << 'EOF'
SUPABASE_URL=https://erjabdqbgancubnqwcdl.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyamFiZHFiZ2FuY3VibnF3Y2RsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0Mzc4NjEsImV4cCI6MjA3ODAxMzg2MX0.thYMfwQHm7Tj4kbmWK8NG79muUkt8trx0ev1rcCxd7w
SUPABASE_SERVICE_KEY=<paste_service_role_key_here>
OPENAI_API_KEY=<your_key>
COMPOSIO_API_KEY=<your_key>
CORS_ALLOW_ORIGINS=http://localhost:5173
EOF

# Update main.py line 1
# Change: from server.api import app
# To:     from server.api_v2 import app

# Run
uv run poke-server
```

### Step 3: Frontend Setup

```bash
cd poke-frontend

# Install
npm install

# Create .env.local
cat > .env.local << 'EOF'
VITE_SUPABASE_URL=https://erjabdqbgancubnqwcdl.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyamFiZHFiZ2FuY3VibnF3Y2RsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0Mzc4NjEsImV4cCI6MjA3ODAxMzg2MX0.thYMfwQHm7Tj4kbmWK8NG79muUkt8trx0ev1rcCxd7w
VITE_API_URL=http://localhost:8000
EOF

# Update main.tsx line 2
# Change: import App from './App.tsx'
# To:     import App from './AppWithAuth.tsx'

# Run
npm run dev
```

### Step 4: Test

1. Open http://localhost:5173
2. Sign up with email/password
3. Send messages
4. Close browser
5. Reopen → Sign in → Messages still there! ✅

---

## 📝 What Changed?

**Before:** Connection ID → In-memory storage → Lost on restart
**After:** Email/Password → JWT Auth → Supabase DB → Persists forever

---

## 🔑 Key Files Modified

- `poke-backend/main.py` - Import `api_v2` instead of `api`
- `poke-frontend/src/main.tsx` - Import `AppWithAuth` instead of `App`

---

## 📚 Full Documentation

- **Complete Setup:** `SUPABASE_MIGRATION.md`
- **Deployment:** `DEPLOYMENT.md`
- **Summary:** `IMPLEMENTATION_SUMMARY.md`

---

## 🆘 Common Issues

**"Module not found: supabase"**
→ Run `uv sync` or `npm install`

**"Invalid JWT"**
→ Check `.env` has correct `SUPABASE_KEY`

**CORS errors**
→ Add frontend URL to `CORS_ALLOW_ORIGINS` in backend `.env`

**Can't find service_role key**
→ https://supabase.com/dashboard/project/erjabdqbgancubnqwcdl/settings/api

---

That's it! User accounts are working. 🎉

