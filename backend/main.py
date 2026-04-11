"""
FastAPI backend for Gmail Client.
All async operations (fetch, delete) run as background tasks.
Browser just polls for current state — refresh-safe.
"""

import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel

from gmail_service import GmailService

load_dotenv()

# ── Singleton service ────────────────────────────────────────────
gmail = GmailService()

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "200"))

# ── Auto-pull state ──────────────────────────────────────────────
auto_pull_task: asyncio.Task | None = None
auto_pull_interval: int = 0  # seconds, 0 = off


async def _auto_pull_loop():
    """Background loop that periodically pulls new emails."""
    while True:
        await asyncio.sleep(auto_pull_interval)
        if gmail.is_authenticated() and auto_pull_interval > 0 and not gmail.is_busy():
            gmail.start_refresh(batch_size=BATCH_SIZE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup, try to restore saved session
    gmail.try_restore()
    yield
    # Cleanup on shutdown
    global auto_pull_task
    if auto_pull_task:
        auto_pull_task.cancel()


app = FastAPI(title="Gmail Client API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ───────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    app_password: str
    lock_code: str

class UnlockRequest(BaseModel):
    lock_code: str


class DeleteRequest(BaseModel):
    uids: list[str]


class DeleteBySenderRequest(BaseModel):
    sender_email: str


class BulkDeleteSendersRequest(BaseModel):
    sender_emails: list[str]


class AutoPullRequest(BaseModel):
    interval: int


# ── Auth endpoints ───────────────────────────────────────────────

@app.get("/api/auth/status")
def auth_status():
    """Check if user is authenticated (survives browser refresh + app restart)."""
    authenticated = gmail.is_authenticated()
    result = {"authenticated": authenticated}
    if authenticated:
        result["profile"] = gmail.get_profile()
    return result


@app.post("/api/auth/login")
def login(req: LoginRequest):
    """Login with email + app password. Session is persisted to disk."""
    try:
        gmail.authenticate(req.email, req.app_password, req.lock_code)
        return {"success": True, "profile": gmail.get_profile()}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/logout")
def logout():
    """Disconnect, cancel all tasks, clear saved session."""
    global auto_pull_task, auto_pull_interval
    if auto_pull_task and not auto_pull_task.done():
        auto_pull_task.cancel()
        auto_pull_task = None
    auto_pull_interval = 0
    gmail.logout()
    return {"success": True}

@app.post("/api/auth/verify-lock")
def verify_lock(req: UnlockRequest):
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    if gmail.verify_lock(req.lock_code):
        return {"success": True}
    raise HTTPException(status_code=401, detail="Invalid lock code")


# ── Background task triggers ─────────────────────────────────────
# These return immediately. Browser polls /api/emails/progress.

@app.post("/api/emails/fetch")
async def start_fetch():
    """Start a full email fetch in the background."""
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    if gmail.is_busy():
        return {"started": False, "reason": "Another operation is already running"}
    gmail.start_full_fetch(batch_size=BATCH_SIZE)
    return {"started": True}


@app.post("/api/emails/refresh")
async def start_refresh():
    """Start an incremental fetch (new emails only) in the background."""
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    if gmail.is_busy():
        return {"started": False, "reason": "Another operation is already running"}
    gmail.start_refresh(batch_size=BATCH_SIZE)
    return {"started": True}


@app.post("/api/emails/delete")
async def start_delete(req: DeleteRequest):
    """Delete emails by UIDs in the background."""
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    if gmail.is_busy():
        return {"started": False, "reason": "Another operation is already running"}
    gmail.start_delete(req.uids)
    return {"started": True, "count": len(req.uids)}


@app.post("/api/emails/delete-by-sender")
async def start_delete_by_sender(req: DeleteBySenderRequest):
    """Delete all emails from a sender in the background."""
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    if gmail.is_busy():
        return {"started": False, "reason": "Another operation is already running"}
    gmail.start_delete_by_sender(req.sender_email)
    return {"started": True, "sender": req.sender_email}


@app.post("/api/emails/delete-bulk-senders")
async def start_delete_bulk_senders(req: BulkDeleteSendersRequest):
    """Delete all emails from multiple senders in the background."""
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    if gmail.is_busy():
        return {"started": False, "reason": "Another operation is already running"}
    gmail.start_bulk_delete_by_senders(req.sender_emails)
    return {"started": True, "count": len(req.sender_emails)}


# ── State polling (browser reads this) ───────────────────────────

@app.get("/api/emails/progress")
def get_progress():
    """Get current operation progress. Browser polls this."""
    return gmail.progress.to_dict()


@app.get("/api/emails")
def get_emails(
    search: str = Query(default=""),
    sort_by: str = Query(default="date"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    """Get fetched emails with search, sort, pagination."""
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")

    emails = gmail.search_emails(search) if search else gmail.get_emails()

    sort_key_map = {"date": "timestamp", "sender": "sender_name", "subject": "subject"}
    key = sort_key_map.get(sort_by, "timestamp")
    reverse = sort_order == "desc"
    emails.sort(key=lambda e: e.get(key, ""), reverse=reverse)

    total = len(emails)
    start = (page - 1) * page_size
    page_emails = emails[start : start + page_size]

    return {
        "emails": page_emails,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@app.get("/api/emails/senders")
def get_senders(
    search: str = Query(default=""),
    sort_by: str = Query(default="total"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=500),
):
    """Get email stats grouped by sender."""
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")

    stats = gmail.get_sender_stats(search=search)
    sort_key_map = {"total": "total", "unread": "unread", "name": "sender_name"}
    key = sort_key_map.get(sort_by, "total")
    reverse = sort_order == "desc"
    stats.sort(key=lambda s: s.get(key, ""), reverse=reverse)

    total = len(stats)
    start = (page - 1) * page_size
    page_stats = stats[start : start + page_size]

    return {
        "senders": page_stats,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@app.get("/api/emails/summary")
def get_summary():
    if not gmail.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    return gmail.get_summary()


# ── Auto-pull config ─────────────────────────────────────────────

@app.get("/api/auto-pull")
def get_auto_pull():
    return {"enabled": auto_pull_interval > 0, "interval": auto_pull_interval}


@app.post("/api/auto-pull")
async def set_auto_pull(req: AutoPullRequest):
    global auto_pull_interval, auto_pull_task

    auto_pull_interval = max(0, req.interval)

    if auto_pull_task and not auto_pull_task.done():
        auto_pull_task.cancel()
        auto_pull_task = None

    if auto_pull_interval > 0:
        auto_pull_task = asyncio.create_task(_auto_pull_loop())

    return {"enabled": auto_pull_interval > 0, "interval": auto_pull_interval}


# ── Static SPA Routing ───────────────────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    @app.exception_handler(404)
    async def fallback_to_index(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(os.path.join(static_dir, "index.html"))

# ── Run server ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
