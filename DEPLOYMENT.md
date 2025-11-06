# Deployment Guide - Vercel + Supabase

## Prerequisites

1. ✅ Supabase project set up (Carl Chat - `erjabdqbgancubnqwcdl`)
2. ✅ Database schema applied
3. ✅ Backend code updated with Supabase
4. ✅ Frontend code updated with authentication
5. GitHub repository (for Vercel deployment)

## Deploy Frontend to Vercel

### Option 1: Using Vercel CLI

1. **Install Vercel CLI**
```bash
npm i -g vercel
```

2. **Login to Vercel**
```bash
vercel login
```

3. **Deploy Frontend**
```bash
cd poke-frontend
vercel
```

4. **Set Environment Variables**
During deployment or in Vercel dashboard:
```
VITE_SUPABASE_URL=https://erjabdqbgancubnqwcdl.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyamFiZHFiZ2FuY3VibnF3Y2RsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0Mzc4NjEsImV4cCI6MjA3ODAxMzg2MX0.thYMfwQHm7Tj4kbmWK8NG79muUkt8trx0ev1rcCxd7w
VITE_API_URL=https://your-backend-url.com
```

5. **Deploy to Production**
```bash
vercel --prod
```

### Option 2: Using Vercel Dashboard

1. **Connect GitHub**
   - Go to https://vercel.com
   - Click "Add New Project"
   - Import your GitHub repository

2. **Configure Project**
   - **Framework Preset**: Vite
   - **Root Directory**: `poke-frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

3. **Add Environment Variables**
   - Settings → Environment Variables
   - Add the three variables above
   - Make sure they're available for all environments

4. **Deploy**
   - Click "Deploy"
   - Vercel will build and deploy automatically

## Deploy Backend

### Option 1: Vercel Serverless Functions

You can deploy the FastAPI backend as Vercel serverless functions:

1. **Create vercel.json in poke-backend**
```json
{
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "main.py"
    }
  ]
}
```

2. **Deploy**
```bash
cd poke-backend
vercel
```

3. **Set Environment Variables**
```
SUPABASE_URL=https://erjabdqbgancubnqwcdl.supabase.co
SUPABASE_KEY=<anon_key>
SUPABASE_SERVICE_KEY=<service_role_key>
OPENAI_API_KEY=<your_key>
COMPOSIO_API_KEY=<your_key>
CORS_ALLOW_ORIGINS=https://your-frontend.vercel.app
```

### Option 2: Railway / Render / Fly.io

For long-running backend processes (WebSockets, background workers):

**Railway**
1. Connect GitHub repo
2. Select `poke-backend` directory
3. Add environment variables
4. Deploy

**Render**
1. New Web Service
2. Connect repository
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn server.api_v2:app --host 0.0.0.0 --port $PORT`

**Fly.io**
1. Install flyctl: `brew install flyctl`
2. Login: `fly auth login`
3. Create `fly.toml` in poke-backend
4. Deploy: `fly launch`

## Update Frontend API URL

After deploying backend, update frontend environment variable:

```bash
# In Vercel dashboard
VITE_API_URL=https://your-backend-url.com
```

Then redeploy frontend.

## Configure CORS

Update backend CORS to allow your Vercel frontend:

```python
# In .env
CORS_ALLOW_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```

## Enable Supabase Realtime (Optional)

For real-time message updates:

1. **In Supabase Dashboard**
   - Database → Replication
   - Enable replication for `messages` and `conversations` tables

2. **In Frontend**
   - Replace polling with Supabase subscriptions
   - See `SUPABASE_MIGRATION.md` for code examples

## DNS & Custom Domain

1. **In Vercel**
   - Settings → Domains
   - Add custom domain
   - Follow DNS configuration instructions

2. **Update Environment Variables**
   - Update CORS_ALLOW_ORIGINS
   - Update VITE_API_URL if using custom backend domain

## Post-Deployment Checklist

- [ ] Frontend deployed and accessible
- [ ] Backend deployed and accessible
- [ ] Environment variables set correctly
- [ ] CORS configured properly
- [ ] Test signup/login flow
- [ ] Test message sending
- [ ] Verify data persists across sessions
- [ ] Check Supabase logs for any RLS issues

## Monitoring

### Vercel
- View logs in Vercel dashboard
- Set up monitoring and alerts
- Check Analytics for performance

### Supabase
- Database → Logs for query performance
- Auth → Users to monitor signups
- Database → Disk usage to monitor growth

## Troubleshooting

### CORS Errors
- Check CORS_ALLOW_ORIGINS includes your Vercel domain
- Verify no trailing slashes in URLs

### Authentication Errors
- Verify environment variables are set
- Check Supabase project is active
- Verify anon key is correct

### Database Errors
- Check RLS policies allow user access
- Verify service_role key for backend operations
- Check Supabase logs for detailed errors

## Scaling Considerations

### Database
- Monitor connection pooling
- Add indexes as needed
- Consider read replicas for high traffic

### Backend
- Use Vercel Edge Functions for faster response
- Implement caching with Redis
- Consider rate limiting

### Frontend
- Enable CDN caching
- Optimize bundle size
- Implement lazy loading

