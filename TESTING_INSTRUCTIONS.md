# 🧪 Testing Instructions - Clear Browser Cache Issue

## The Problem
Your browser has cached the old JavaScript that calls the wrong endpoint. The server logs show:
```
INFO: 127.0.0.1:54772 - "POST /api/analyse/comprehensive HTTP/1.1" 500 Internal Server Error
```

This means the browser is still using the OLD cached JavaScript.

## Solution: Use the Test Page

I've created a simple test page that bypasses the cache issue.

### Step 1: Open the Test Page
Open your browser and go to:
```
http://localhost:8080/test
```

### Step 2: Test the Analysis
1. Select a technique (spike, serve, block, or dig)
2. Upload a volleyball video
3. Click "🚀 Test Analysis"
4. Wait for the result

### Expected Result
✅ Analysis should complete successfully
✅ You'll see JSON response with analysis data
✅ No 500 errors

---

## Alternative: Clear Browser Cache

If you want to use the main interface at http://localhost:8080:

### Option A: Hard Refresh (Recommended)
1. Open http://localhost:8080
2. Press **Ctrl + Shift + R** (Windows) or **Cmd + Shift + R** (Mac)
3. This forces the browser to reload all files, ignoring cache

### Option B: Clear Cache Manually
1. Press **F12** to open Developer Tools
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Option C: Incognito/Private Window
1. Open a new Incognito/Private window
2. Go to http://localhost:8080
3. The cache won't be used

---

## Verify the Fix

After clearing cache or using the test page, check the browser console (F12):
- You should see: `Target API: http://localhost:8080/api/analyse/auto`
- NOT: `Target API: http://localhost:8080/api/analyse/comprehensive`

---

## Server Status

The server should show this when you upload:
```
INFO: 127.0.0.1:XXXXX - "POST /api/analyse/auto HTTP/1.1" 200 OK
```

NOT this:
```
INFO: 127.0.0.1:XXXXX - "POST /api/analyse/comprehensive HTTP/1.1" 500 Internal Server Error
```

---

## Quick Test URLs

- **Test Page:** http://localhost:8080/test (NEW - no cache issues)
- **Main Interface:** http://localhost:8080 (requires cache clear)
- **API Docs:** http://localhost:8080/api/docs
- **Health Check:** http://localhost:8080/api/health

---

## What to Do Now

1. **FIRST:** Try the test page at http://localhost:8080/test
2. If that works, then clear your browser cache
3. Then try the main interface at http://localhost:8080

The test page will prove the endpoint works correctly! 🚀
