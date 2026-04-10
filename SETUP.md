# Gmail Client - Setup Guide

## Prerequisites
- Python 3.10+
- Node.js 18+
- A Gmail account with 2-Step Verification enabled

## Step 1: Get a Gmail App Password

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. If prompted, enable **2-Step Verification** first
3. Select app: **Mail**, device: **Other** (type "Gmail Client")
4. Click **Generate**
5. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)

That's it for setup — no Google Cloud Console, no credentials files.

## Step 2: Run the app

### Windows
```
start.bat
```

### Mac / Linux
```bash
chmod +x start.sh
./start.sh
```

### Manual start
```bash
# Terminal 1 - Backend
cd backend
pip install -r requirements.txt
python main.py

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

## Step 3: Open in browser

Go to **http://localhost:3000**, enter your Gmail address and the app password, and click Sign In.

The app will connect via IMAP and start fetching all your email headers in the background. You'll see a progress bar showing how many emails have been loaded.

## Architecture

```
Gmail Client/
  backend/
    main.py            # FastAPI server with REST + SSE endpoints
    gmail_service.py   # IMAP client (auth, batch fetch, search, stats)
    requirements.txt
  frontend/
    src/
      App.vue                 # Root component
      main.js                 # Vue + Pinia setup
      services/api.js         # Axios API client
      stores/emailStore.js    # Pinia state management
      components/
        LoginScreen.vue       # Email + app password login
        ProgressBar.vue       # Real-time fetch progress
        SummaryBar.vue        # Stats (total/read/unread/senders)
        Toolbar.vue           # Search + sort + view toggle
        EmailList.vue         # Email table with pagination
        SenderList.vue        # Group-by-sender view with stats
```

## Extending

**Backend:** Add new methods to `GmailService` class in `gmail_service.py`, then expose them as endpoints in `main.py`.

**Frontend:** Create new Vue components in `components/`, add state/actions to `emailStore.js`, and wire them into `App.vue`.
