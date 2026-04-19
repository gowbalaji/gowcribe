# Gowcribe

Tamil audio transcription — up to 1 hour / 600 MB. Outputs `.txt` and `.srt`.

---

## One-time setup (do this once, takes ~15 minutes)

### 1. Groq API key (free)

1. Go to [console.groq.com](https://console.groq.com) and sign up
2. Go to **API Keys → Create API Key**
3. Copy the key — you'll use it as `GROQ_API_KEY`

---

### 2. Google OAuth credentials (free)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project → New Project** → name it `gowcribe` → Create
3. In the left menu: **APIs & Services → OAuth consent screen**
   - User type: **External** → Create
   - App name: `Gowcribe`, your email for support
   - Click **Save and Continue** through all steps (no extra scopes needed)
   - Under **Test users**, add all Gmail addresses that need access
4. Left menu: **APIs & Services → Credentials → + Create Credentials → OAuth client ID**
   - Application type: **Web application**
   - Name: `Gowcribe`
   - Authorised redirect URIs: `https://YOUR-APP.railway.app/auth/callback`
     *(fill in the Railway URL after deploy — you can update this)*
   - Click **Create** → copy **Client ID** and **Client Secret**

---

### 3. Deploy to Railway (free tier)

1. Push this repo to GitHub (make sure `.env` is NOT committed — it's in `.gitignore`)
2. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**
3. Select this repo → Railway auto-detects the Dockerfile
4. Go to your service → **Variables** tab → add these:

```
GROQ_API_KEY        = your_groq_key
GOOGLE_CLIENT_ID    = your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET= your_client_secret
SECRET_KEY          = run: openssl rand -hex 32
ALLOWED_EMAILS      = gowbalaji88@gmail.com,teammate@gmail.com
REDIRECT_URI        = https://YOUR-APP.railway.app/auth/callback
```

5. Go to **Settings → Networking → Generate Domain** → copy your Railway URL
6. Go back to Google Cloud Console → update the redirect URI with the real Railway URL
7. Railway redeploys automatically — takes ~2 min

---

## Adding team members

In Railway **Variables**, add their Gmail to `ALLOWED_EMAILS` (comma-separated). No redeploy needed — Railway applies env var changes live.

---

## Local development

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # fill in your values, set REDIRECT_URI=http://localhost:8000/auth/callback
uvicorn main:app --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev   # runs on http://localhost:5173 (proxies /api and /auth to backend)
```

---

## How it works

1. Upload audio → backend streams to disk (no RAM spike)
2. `ffmpeg` splits into 10-min / ~2 MB chunks
3. Each chunk → Groq `whisper-large-v3` with `language=ta`
4. Live progress bar via Server-Sent Events
5. Chunks joined → `.txt` (plain) + `.srt` (with timestamps)
6. Files deleted from server after download
