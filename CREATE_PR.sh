#!/bin/bash
set -e

cd /Users/jesserose/open-poke

echo "🔍 Checking current branch..."
BRANCH=$(git branch --show-current)
echo "Current branch: $BRANCH"

# Show current status
echo -e "\n📝 Git Status:"
git status --short

# Add all changes
echo -e "\n➕ Adding all changes..."
git add .

# Create commit
echo -e "\n💾 Creating commit..."
git commit -m "Add Supabase authentication and persistent storage

Features:
- User accounts with email/password authentication
- JWT-based secure sessions with Supabase Auth
- PostgreSQL database with Row Level Security policies
- Messages and conversations persist across sessions
- New AuthForm component for login/signup UI
- AppWithAuth component for authenticated chat flow

Backend Changes:
- Created database.py for Supabase operations wrapper
- Created auth.py for JWT authentication service
- Created api_v2.py with protected endpoints
- Updated message_processor_v2.py to save to database
- Fixed service_role key usage for bypassing RLS

Database Schema:
- profiles table (extends auth.users)
- conversations table with user relationship
- messages table with conversation relationship
- user_memories table for insights

Documentation:
- SUPABASE_MIGRATION.md - Complete setup guide
- DEPLOYMENT.md - Vercel deployment instructions  
- QUICK_START.md - 5-minute setup guide
- IMPLEMENTATION_SUMMARY.md - Full overview

Tested:
- User signup and login working
- Messages persist across logout/login
- AI responses save to database correctly
"

# Push
echo -e "\n🚀 Pushing to remote..."
git push

# Show what we have on this branch
echo -e "\n📋 Recent commits on this branch:"
git log --oneline -10

# Create PR
echo -e "\n🎯 Creating Pull Request..."
gh pr create --title "Add Supabase Authentication & Persistent Storage" --body "## 🎯 Summary
Complete implementation of user authentication and persistent storage using Supabase.

## ✨ Key Features
- ✅ User accounts with email/password
- ✅ JWT-based authentication  
- ✅ PostgreSQL database with Row Level Security
- ✅ Messages persist across sessions
- ✅ Conversation history saved permanently
- ✅ Professional login/signup UI

## 🔧 Technical Implementation

### Database (Supabase)
- profiles, conversations, messages, user_memories tables
- Row Level Security policies
- Auto-triggers for profile creation

### Backend
- database.py - Supabase operations
- auth.py - JWT authentication
- api_v2.py - Protected endpoints
- message_processor_v2.py - Database integration

### Frontend  
- AuthForm.tsx - Login/signup component
- AppWithAuth.tsx - Authenticated wrapper
- Supabase client integration

## 📚 Documentation
- SUPABASE_MIGRATION.md
- DEPLOYMENT.md
- QUICK_START.md

## ✅ Tested
- Signup/login working
- Messages persist across sessions
- AI responses saved to DB
"

echo -e "\n✅ Done! PR created successfully"
