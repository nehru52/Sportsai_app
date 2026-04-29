# 🌐 Public Deployment Guide - SportsAI

## Overview

To make your SportsAI app publicly accessible, you need to:
1. Expose the backend API (port 8001) publicly
2. Expose the frontend (port 3000) publicly
3. Update the frontend to use the public backend URL

---

## Option 1: Using Ngrok (Recommended - Easy & Fast)

### Step 1: Install Ngrok

**Download:**
1. Go to https://ngrok.com/download
2. Download the Windows version
3. Extract `ngrok.exe` to a folder (e.g., `C:\ngrok\`)
4. Add to PATH or run from that folder

**Or install via Chocolatey:**
```powershell
choco install ngrok
```

### Step 2: Sign Up & Get Auth Token

1. Sign up at https://dashboard.ngrok.com/signup
2. Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
3. Run: `ngrok config add-authtoken YOUR_TOKEN_HERE`

### Step 3: Start Backend Tunnel

Open a new terminal and run:
```powershell
ngrok http 8001
```

You'll see output like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8001
```

**Copy the HTTPS URL** (e.g., `https://abc123.ngrok-free.app`)

### Step 4: Start Frontend Tunnel

Open another terminal and run:
```powershell
ngrok http 3000
```

You'll see:
```
Forwarding  https://xyz789.ngrok-free.app -> http://localhost:3000
```

**Copy this URL** for accessing the frontend.

### Step 5: Update Frontend to Use Public Backend

Edit `frontend/app.js` line 4:

```javascript
const API = window.location.hostname === 'localhost' 
  ? 'http://localhost:8001' 
  : 'https://YOUR-BACKEND-NGROK-URL.ngrok-free.app';  // Replace with your backend URL
```

### Step 6: Access Your App

Open the frontend URL in any browser:
```
https://xyz789.ngrok-free.app/index_launcher.html
```

**Note:** Ngrok free tier shows a warning page first - click "Visit Site" to continue.

---

## Option 2: Using Cloudflare Tunnel (Free, No Account Needed)

### Step 1: Install Cloudflared

**Download:**
1. Go to https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
2. Download Windows version
3. Extract to a folder

### Step 2: Start Backend Tunnel

```powershell
cloudflared tunnel --url http://localhost:8001
```

Copy the public URL (e.g., `https://abc-def-ghi.trycloudflare.com`)

### Step 3: Start Frontend Tunnel

```powershell
cloudflared tunnel --url http://localhost:3000
```

Copy the frontend URL.

### Step 4: Update Frontend

Same as ngrok - update `frontend/app.js` with the backend URL.

---

## Option 3: Deploy to Cloud (Production)

### Frontend Deployment Options:

**1. Vercel (Easiest)**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy frontend
cd frontend
vercel
```

**2. Netlify**
```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
cd frontend
netlify deploy
```

**3. GitHub Pages**
1. Push frontend folder to GitHub
2. Enable GitHub Pages in repo settings
3. Select branch and `/frontend` folder

### Backend Deployment Options:

**1. Railway.app (Free tier)**
1. Sign up at https://railway.app
2. Create new project
3. Deploy from GitHub or upload code
4. Set environment variables
5. Get public URL

**2. Render.com (Free tier)**
1. Sign up at https://render.com
2. Create new Web Service
3. Connect GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`

**3. Heroku**
```bash
# Install Heroku CLI
# Create Procfile:
echo "web: uvicorn api:app --host 0.0.0.0 --port $PORT" > Procfile

# Deploy
heroku create your-app-name
git push heroku main
```

---

## Current Setup (From Previous Session)

Based on your previous setup:

**Backend URL:** `https://2a54-82-11-179-110.ngrok-free.app`  
**Frontend URL:** `https://breezy-hotels-make.loca.lt`

These URLs expire when you close the tunnels. You need to restart them.

---

## Quick Start (Ngrok Method)

### Terminal 1 - Backend Server:
```powershell
cd C:\sportsai-backend
uvicorn api:app --reload --port 8001
```

### Terminal 2 - Backend Tunnel:
```powershell
ngrok http 8001
# Copy the HTTPS URL
```

### Terminal 3 - Frontend Server:
```powershell
cd C:\sportsai-backend\frontend
python -m http.server 3000
```

### Terminal 4 - Frontend Tunnel:
```powershell
ngrok http 3000
# Copy the HTTPS URL
```

### Update Frontend:
Edit `frontend/app.js` line 4 with your backend ngrok URL.

### Access:
Open the frontend ngrok URL in your browser.

---

## Sharing with Others

Once deployed, share:
- **Frontend URL** - This is what users open in their browser
- **API Docs** - Add `/docs` to backend URL (e.g., `https://abc123.ngrok-free.app/docs`)

Example:
```
Frontend: https://xyz789.ngrok-free.app/index_launcher.html
API Docs: https://abc123.ngrok-free.app/docs
```

---

## Troubleshooting

### Ngrok "Too Many Connections"
- Free tier limits to 1 connection per account
- Use 2 accounts or upgrade to paid plan
- Or use Cloudflare Tunnel (unlimited)

### CORS Errors
Add to `api.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Ngrok Warning Page
- This is normal for free tier
- Users must click "Visit Site" to continue
- Upgrade to paid plan to remove

### Tunnel Disconnects
- Free tunnels expire after inactivity
- Restart the tunnel command
- Update frontend with new URL

---

## Security Notes

⚠️ **Important for Production:**

1. **Don't expose development server publicly long-term**
2. **Add authentication** to your API
3. **Use HTTPS only** (ngrok/cloudflare provide this)
4. **Rate limiting** - prevent abuse
5. **Input validation** - already in place
6. **Environment variables** - don't hardcode URLs

---

## Cost Comparison

| Service | Free Tier | Paid |
|---------|-----------|------|
| Ngrok | 1 tunnel, 40 req/min | $8/mo - 3 tunnels |
| Cloudflare Tunnel | Unlimited | Free |
| Vercel | 100GB bandwidth | $20/mo |
| Railway | $5 credit/mo | Pay as you go |
| Render | 750 hours/mo | $7/mo |

---

## Recommended Setup

**For Testing/Sharing:**
- Use Ngrok or Cloudflare Tunnel
- Quick and easy
- No deployment needed

**For Production:**
- Frontend: Vercel or Netlify
- Backend: Railway or Render
- Custom domain
- SSL certificates (automatic)
- Better performance

---

## Next Steps

1. Choose deployment method (Ngrok recommended for quick sharing)
2. Install required tools
3. Start tunnels/deploy
4. Update frontend with backend URL
5. Test the public URL
6. Share with others!

Need help with any specific step? Let me know!
