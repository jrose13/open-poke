#!/bin/bash

# PR Creation Script
# Run this in a fresh terminal

cd /Users/jesserose/open-poke

# Check status
echo "=== Current Status ==="
git status

# Add all changes
echo -e "\n=== Adding Changes ==="
git add .

# Create commit
echo -e "\n=== Creating Commit ==="
git commit -m "Add Supabase authentication and persistent storage

- Set up Supabase Carl Chat project with database schema
- Implement JWT-based authentication with email/password
- Create AuthForm component for login/signup UI
- Migrate backend from in-memory to Supabase database storage
- Add database.py and auth.py modules for Supabase integration
- Update message processor to save messages to database
- Fix service_role key usage for database operations
- All user messages and AI responses now persist across sessions
- Created comprehensive documentation (SUPABASE_MIGRATION.md, DEPLOYMENT.md)
"

# Push changes
echo -e "\n=== Pushing Changes ==="
git push

# Show commit log
echo -e "\n=== Commits on This Branch ==="
git log main..HEAD --oneline

# Show changed files
echo -e "\n=== Changed Files ==="
git diff --name-status main

# Create PR
echo -e "\n=== Creating PR ==="
gh pr create --title "Add Supabase Authentication & Persistent Storage" --body "## Summary
Implements complete user authentication and persistent storage system using Supabase.

## Key Features
- ✅ User accounts with email/password authentication
- ✅ JWT-based secure sessions
- ✅ PostgreSQL database with Row Level Security
- ✅ Messages and conversations persist across sessions
- ✅ New AuthForm UI component for login/signup
- ✅ Backend migrated from in-memory to Supabase

## Technical Changes
- Created Supabase database schema (profiles, conversations, messages, user_memories)
- Implemented authentication service with JWT verification
- Added database operations wrapper for Supabase
- Updated message processor to save to database
- Created AppWithAuth.tsx for authenticated chat flow
- Added comprehensive documentation

## Documentation
- SUPABASE_MIGRATION.md - Complete setup guide
- DEPLOYMENT.md - Vercel deployment instructions
- QUICK_START.md - Get running in 5 minutes

## Testing
Tested locally with successful:
- User signup/login
- Message persistence across sessions
- AI agent responses saving to database
"

echo -e "\n=== Done! ==="

