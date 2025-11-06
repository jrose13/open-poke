# Supabase Migration Guide

This guide will help you complete the migration to Supabase for user authentication and persistent storage.

## ✅ Completed

1. **Database Schema** - Created tables for profiles, conversations, messages, and user_memories
2. **Row Level Security** - Enabled RLS with policies to protect user data
3. **Backend Code** - Created new modules:
   - `server/database.py` - Supabase database operations
   - `server/auth.py` - Authentication service
   - `server/api_v2.py` - Updated API with auth
4. **Frontend Dependencies** - Added `@supabase/supabase-js`
5. **Frontend Components** - Created `AuthForm.tsx` and `supabase.ts`

## 🔧 Setup Instructions

### 1. Backend Setup

#### Install Dependencies
```bash
cd poke-backend
uv sync
```

#### Get Service Role Key
1. Go to https://supabase.com/dashboard/project/erjabdqbgancubnqwcdl/settings/api
2. Copy the `service_role` key (starts with `eyJ...`)
3. **Keep this secret - it has full database access**

#### Create .env file
Create `/Users/jesserose/open-poke/poke-backend/.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://erjabdqbgancubnqwcdl.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyamFiZHFiZ2FuY3VibnF3Y2RsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0Mzc4NjEsImV4cCI6MjA3ODAxMzg2MX0.thYMfwQHm7Tj4kbmWK8NG79muUkt8trx0ev1rcCxd7w
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Your existing keys
OPENAI_API_KEY=your_openai_key
COMPOSIO_API_KEY=your_composio_key
COMPOSIO_AUTH_CONFIG_ID=gmail

# CORS
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

#### Update main.py to use new API
Replace `main.py` to import from `api_v2`:

```python
from server.api_v2 import app

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
```

### 2. Frontend Setup

#### Install Dependencies
```bash
cd poke-frontend
npm install
```

#### Create .env.local file
Create `/Users/jesserose/open-poke/poke-frontend/.env.local`:

```bash
VITE_SUPABASE_URL=https://erjabdqbgancubnqwcdl.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyamFiZHFiZ2FuY3VibnF3Y2RsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0Mzc4NjEsImV4cCI6MjA3ODAxMzg2MX0.thYMfwQHm7Tj4kbmWK8NG79muUkt8trx0ev1rcCxd7w
VITE_API_URL=http://localhost:8000
```

#### Update App.tsx
Update the main `App.tsx` to use Supabase authentication - see example in next section.

### 3. Optional: Enable Supabase Realtime

To replace WebSocket with Supabase Realtime:

```sql
-- In Supabase SQL Editor
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE conversations;
```

Then in frontend:
```typescript
import { supabase } from './supabase';

// Subscribe to new messages
supabase
  .channel('messages')
  .on('postgres_changes', 
    { event: 'INSERT', schema: 'public', table: 'messages' },
    (payload) => {
      console.log('New message:', payload);
    }
  )
  .subscribe();
```

## 📝 Key Changes

### Authentication Flow
**Old:** Connection ID based sessions (in-memory, lost on restart)
**New:** JWT-based Supabase Auth (persistent, secure)

### Data Storage
**Old:** In-memory dictionaries
**New:** PostgreSQL with Row Level Security

### API Endpoints

#### New Auth Endpoints
- `POST /auth/signup` - Register new user
- `POST /auth/signin` - Login existing user
- `POST /auth/refresh` - Refresh expired session
- `GET /auth/me` - Get current user

#### Updated Endpoints (now require auth)
- `GET /conversations` - Get user's conversations
- `POST /conversations` - Create new conversation
- `POST /messages` - Send message (auto-creates conversation)
- `GET /memories` - Get user memories
- `WS /ws/users/me?token=<jwt>` - WebSocket with auth

## 🚀 Testing

1. Start backend: `cd poke-backend && uv run poke-server`
2. Start frontend: `cd poke-frontend && npm run dev`
3. Visit http://localhost:5173
4. Sign up with a new account
5. Test sending messages and see them persist!

## 🔒 Security Notes

- **Never commit** `.env` files
- Service role key has **full database access** - keep it server-side only
- RLS policies protect user data automatically
- JWT tokens expire after 1 hour (configurable in Supabase)

## 📊 Database Schema

```
profiles
├── id (uuid, FK to auth.users)
├── email (text)
├── full_name (text)
├── connection_id (text) - Composio connection
└── timestamps

conversations
├── id (uuid)
├── user_id (uuid, FK to profiles)
├── title (text)
└── timestamps

messages
├── id (uuid)
├── conversation_id (uuid, FK to conversations)
├── user_id (uuid, FK to profiles)
├── content (text)
├── role (user/assistant/system)
└── created_at

user_memories
├── id (uuid)
├── user_id (uuid, FK to profiles)
├── memory_type (text)
├── content (jsonb)
└── timestamps
```

## 🐛 Troubleshooting

### "Invalid JWT" errors
- Check that SUPABASE_KEY is set correctly
- Verify token hasn't expired (refresh if needed)

### "User not found" errors
- Check that RLS policies allow access
- Verify user is authenticated

### Database connection issues
- Verify SUPABASE_URL and keys are correct
- Check Supabase project status in dashboard

