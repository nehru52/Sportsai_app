# 🚀 SportsAI Deployment Guide
## Vercel (Frontend) + Cloudflare (Backend + Storage)

---

## Architecture Overview

```
User Browser
    ↓
Vercel (Frontend - Static Files)
    ↓ API Calls
Cloudflare Workers (Backend - Python API)
    ↓ Storage
Cloudflare R2 (Videos, Models, Outputs)
```

---

## Part 1: Deploy Frontend to Vercel

### Step 1: Install Vercel CLI

```powershell
npm install -g vercel
```

### Step 2: Login to Vercel

```powershell
vercel login
```

### Step 3: Deploy Frontend

```powershell
# Navigate to your project root
cd C:\sportsai-backend

# Deploy
vercel
```

**Follow the prompts:**
- Set up and deploy? `Y`
- Which scope? Select your account
- Link to existing project? `N`
- Project name? `sportsai-frontend`
- Directory? `./frontend`
- Override settings? `N`

**You'll get a URL like:**
```
https://sportsai-frontend.vercel.app
```

### Step 4: Set Production Deployment

```powershell
vercel --prod
```

### Step 5: Configure Environment Variables (Optional)

In Vercel dashboard:
1. Go to your project
2. Settings → Environment Variables
3. Add any needed variables

---

## Part 2: Deploy Backend to Cloudflare Workers

### Step 1: Install Wrangler CLI

```powershell
npm install -g wrangler
```

### Step 2: Login to Cloudflare

```powershell
wrangler login
```

### Step 3: Create R2 Buckets

```powershell
# Create buckets for storage
wrangler r2 bucket create sportsai-videos
wrangler r2 bucket create sportsai-outputs
wrangler r2 bucket create sportsai-models
```

### Step 4: Update Backend for Cloudflare Workers

**Note:** Cloudflare Workers have limitations:
- Max 10ms CPU time per request (not suitable for video processing)
- Better to use Cloudflare Pages Functions or a different backend host

**Alternative: Use Railway/Render for Backend**

Since your backend does heavy video processing (YOLO, 3D pose lifting), Cloudflare Workers won't work well. Use:

---

## Part 2 (Alternative): Deploy Backend to Railway

### Step 1: Install Railway CLI

```powershell
npm install -g @railway/cli
```

### Step 2: Login

```powershell
railway login
```

### Step 3: Initialize Project

```powershell
railway init
```

### Step 4: Deploy

```powershell
railway up
```

### Step 5: Add Environment Variables

```powershell
railway variables set R2_ENDPOINT=https://f76d2ce8d05a169a24d24d6895c13dd7.r2.cloudflarestorage.com
railway variables set R2_ACCESS_KEY=8a88c9ea5c1eab615f51fc6d339e5550
railway variables set R2_SECRET_KEY=0dab2a649eef436523a727b883ef8267731187d906f196e8d47990ea5c012057
```

**You'll get a URL like:**
```
https://sportsai-backend-production.up.railway.app
```

---

## Part 3: Connect Frontend to Backend

### Update Frontend API URL

Edit `frontend/app.js` line 4:

```javascript
const API = window.location.hostname === 'localhost' 
  ? 'http://localhost:8001' 
  : 'https://sportsai-backend-production.up.railway.app';  // Your Railway URL
```

### Redeploy Frontend

```powershell
vercel --prod
```

---

## Part 4: Configure Cloudflare R2 for Public Access

### Option A: Public Bucket (for outputs)

1. Go to Cloudflare Dashboard → R2
2. Select `sportsai-outputs` bucket
3. Settings → Public Access → Enable
4. Copy the public URL: `https://pub-xxxxx.r2.dev`

### Option B: Custom Domain

1. Go to R2 bucket settings
2. Connect custom domain (e.g., `cdn.yourdomain.com`)
3. Update DNS records as instructed

---

## Complete Deployment Commands

### First Time Setup:

```powershell
# 1. Install CLIs
npm install -g vercel @railway/cli wrangler

# 2. Login to services
vercel login
railway login
wrangler login

# 3. Create R2 buckets
wrangler r2 bucket create sportsai-videos
wrangler r2 bucket create sportsai-outputs
wrangler r2 bucket create sportsai-models

# 4. Deploy backend to Railway
railway init
railway up

# 5. Get backend URL
railway status

# 6. Update frontend/app.js with backend URL

# 7. Deploy frontend to Vercel
vercel --prod
```

### Update Deployments:

```powershell
# Update backend
railway up

# Update frontend
vercel --prod
```

---

## Environment Variables Setup

### Backend (Railway):

```env
# Cloudflare R2
R2_ENDPOINT=https://f76d2ce8d05a169a24d24d6895c13dd7.r2.cloudflarestorage.com
R2_ACCESS_KEY=8a88c9ea5c1eab615f51fc6d339e5550
R2_SECRET_KEY=0dab2a649eef436523a727b883ef8267731187d906f196e8d47990ea5c012057
R2_BUCKET_VIDEOS=sportsai-videos
R2_BUCKET_OUTPUTS=sportsai-outputs
R2_BUCKET_MODELS=sportsai-models

# App Config
ENVIRONMENT=production
PORT=8001
```

Set these in Railway dashboard or via CLI:
```powershell
railway variables set KEY=VALUE
```

---

## Update Backend to Use R2 Storage

### Modify `api.py` to save videos to R2:

```python
from r2_storage import upload_video, upload_output, download_video
import tempfile
import os

@app.post("/analyse/auto")
async def analyse_auto(video: UploadFile, ...):
    # Save uploaded video to temp file
    temp_video = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    content = await video.read()
    temp_video.write(content)
    temp_video.close()
    
    # Upload to R2
    video_filename = f"{uuid.uuid4()}.mp4"
    upload_video(temp_video.name, video_filename)
    
    # Process video...
    result = analyse_video_auto(temp_video.name, ...)
    
    # Upload output video to R2
    if os.path.exists(output_path):
        output_filename = f"{uuid.uuid4()}_annotated.mp4"
        upload_output(output_path, output_filename)
        
        # Generate public URL
        public_url = f"https://pub-xxxxx.r2.dev/{output_filename}"
        result['video_url'] = public_url
    
    # Cleanup temp files
    os.unlink(temp_video.name)
    
    return result
```

---

## Testing Deployment

### Test Backend:

```powershell
# Test health endpoint
curl https://sportsai-backend-production.up.railway.app/

# Test API docs
# Open in browser: https://sportsai-backend-production.up.railway.app/docs
```

### Test Frontend:

```
https://sportsai-frontend.vercel.app/index_launcher.html
```

### Test Full Flow:

1. Open frontend URL
2. Upload a video
3. Check if analysis works
4. Verify annotated video plays

---

## Custom Domain Setup

### Frontend (Vercel):

1. Go to Vercel dashboard → Your project
2. Settings → Domains
3. Add domain: `app.yourdomain.com`
4. Update DNS records as instructed

### Backend (Railway):

1. Go to Railway dashboard → Your project
2. Settings → Domains
3. Add domain: `api.yourdomain.com`
4. Update DNS records

### Update Frontend:

```javascript
const API = 'https://api.yourdomain.com';
```

---

## Monitoring & Logs

### Vercel Logs:

```powershell
vercel logs
```

Or view in dashboard: https://vercel.com/dashboard

### Railway Logs:

```powershell
railway logs
```

Or view in dashboard: https://railway.app/dashboard

### Cloudflare R2 Analytics:

View in Cloudflare dashboard → R2 → Analytics

---

## Cost Estimate

### Vercel:
- **Free tier:** 100GB bandwidth/month
- **Pro:** $20/month - 1TB bandwidth

### Railway:
- **Free:** $5 credit/month (~500 hours)
- **Pay as you go:** ~$5-20/month for small app

### Cloudflare R2:
- **Storage:** $0.015/GB/month
- **Class A operations:** $4.50/million (uploads)
- **Class B operations:** $0.36/million (downloads)
- **Egress:** FREE (unlike S3!)

**Estimated monthly cost for 1000 users:**
- Vercel: Free tier sufficient
- Railway: ~$10-15
- R2: ~$5-10
- **Total: ~$15-25/month**

---

## Troubleshooting

### CORS Errors:

Add to `api.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://sportsai-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Large File Uploads:

Railway has 100MB request limit. For larger videos:
1. Use direct R2 upload from frontend
2. Or split video processing into chunks

### Slow Processing:

Railway free tier has limited CPU. Upgrade to:
- Railway Pro: $20/month
- Or use GPU instance for faster YOLO processing

---

## Quick Deploy Script

Save as `deploy.sh`:

```bash
#!/bin/bash

echo "🚀 Deploying SportsAI..."

# Deploy backend
echo "📦 Deploying backend to Railway..."
railway up

# Get backend URL
BACKEND_URL=$(railway status --json | jq -r '.url')
echo "✅ Backend deployed: $BACKEND_URL"

# Update frontend
echo "📝 Updating frontend API URL..."
sed -i "s|https://.*railway.app|$BACKEND_URL|g" frontend/app.js

# Deploy frontend
echo "🌐 Deploying frontend to Vercel..."
vercel --prod

echo "✅ Deployment complete!"
```

Run: `bash deploy.sh`

---

## Next Steps

1. ✅ Deploy frontend to Vercel
2. ✅ Deploy backend to Railway
3. ✅ Configure R2 buckets
4. ✅ Update frontend with backend URL
5. ✅ Test full flow
6. ✅ Add custom domains (optional)
7. ✅ Set up monitoring
8. ✅ Share public URL!

**Your public URLs:**
- Frontend: `https://sportsai-frontend.vercel.app`
- Backend: `https://sportsai-backend-production.up.railway.app`
- API Docs: `https://sportsai-backend-production.up.railway.app/docs`

Share the frontend URL with anyone to let them use your app! 🎉
