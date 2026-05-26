# Vercel Deployment Guide

## Prerequisites
- GitHub account with your repository pushed
- Vercel account (free tier available)

## Step 1: Push to GitHub
Ensure all code is pushed to your GitHub repository:
```bash
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

## Step 2: Deploy on Vercel

### Option A: Via Vercel Dashboard (Recommended)
1. Go to [vercel.com](https://vercel.com)
2. Sign in with GitHub
3. Click "Add New" → "Project"
4. Select your GitHub repository (Srinidhi262005/IDEAHUB)
5. Click "Import"
6. Configure environment variables (see below)
7. Click "Deploy"

### Option B: Via Vercel CLI
```bash
npm i -g vercel
vercel
```

## Step 3: Configure Environment Variables

After deployment starts, go to **Project Settings → Environment Variables** and add:

```
DATABASE_URL=postgresql://user:password@your-postgres-host/ideahub_db
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
```

## Database Setup - Use PostgreSQL (Free Tier Available)

### Recommended Options:

#### 1. **Neon (Recommended - Free with Auto-scaling)**
- Go to [neon.tech](https://neon.tech)
- Sign up with GitHub
- Create a new database
- Copy the connection string
- Add as `DATABASE_URL` in Vercel environment variables

#### 2. **Supabase (PostgreSQL + extras)**
- Go to [supabase.com](https://supabase.com)
- Create new project
- Get PostgreSQL connection string
- Add to Vercel environment variables

#### 3. **Render (Simple option)**
- Go to [render.com](https://render.com)
- Create PostgreSQL database
- Free tier includes 90 days of service

### Update Connection String
In your Flask config, ensure it uses `DATABASE_URL`:
```python
import os
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
```

## Step 4: Run Database Migrations

After first deployment:
1. In Vercel dashboard, go to Deployments
2. Click on your deployment
3. Go to "Function Logs"
4. Run migrations via CLI or manually initialize database

## Important Notes

- **SQLite won't work** on Vercel (ephemeral filesystem). Use PostgreSQL only.
- **File uploads**: Currently stored locally. For production, use:
  - Vercel Blob Storage
  - AWS S3
  - Cloudinary
  
- **WebSocket Support**: SocketIO included but needs configuration for serverless

## Troubleshooting

If deployment fails:
1. Check **Logs** in Vercel dashboard
2. Ensure `DATABASE_URL` is set correctly
3. Verify all required packages in `requirements.txt`
4. Run `vercel logs` to see detailed errors

## Next Steps After Deployment

1. Update your database from local to Neon/Supabase
2. Configure storage for file uploads
3. Update domain in DNS settings
4. Set up environment-specific configs (.env.production)

---

For live support: Visit Vercel documentation at [vercel.com/docs](https://vercel.com/docs)
