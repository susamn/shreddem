"""
Gmail IMAP service module.
- Uses IMAP UIDs (stable, unique) instead of sequence numbers.
- Runs fetch/delete as background tasks independent of browser.
- Persists session to survive app restart.
"""

import imaplib
import email
import email.utils
import email.header
import asyncio
import json
import logging
import base64
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

import db

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
from db import CONFIG_DIR
SESSION_FILE = CONFIG_DIR / "session.json"
NUM_WORKERS = 4  # Number of parallel IMAP connections for fetching

FOLDER_CANDIDATES = [
    '"[Gmail]/All Mail"',
    '"[Gmail]/Tous les messages"',
    '"[Gmail]/Alle Nachrichten"',
    '"[Gmail]/Todos"',
    '"[Gmail]/Tutti i messaggi"',
    "INBOX",
]

TRASH_CANDIDATES = [
    '"[Gmail]/Trash"',
    '"[Gmail]/Corbeille"',
    '"[Gmail]/Papierkorb"',
    '"[Gmail]/Papelera"',
    '"[Gmail]/Cestino"',
]


def decode_header_value(raw: str) -> str:
    """Decode MIME-encoded header values."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


@dataclass
class EmailHeader:
    """Represents the metadata of a single email. uid is the stable IMAP UID."""
    uid: str
    subject: str
    sender_email: str
    sender_name: str
    date: str
    timestamp: float
    is_read: bool
    labels: list[str] = field(default_factory=list)
    snippet: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ActionProgress:
    """Tracks progress of any background operation."""
    total: int = 0
    processed: int = 0
    status: str = "idle"  # idle | discovering | fetching | deleting | done | error
    action: str = "fetch"  # fetch | delete
    error: Optional[str] = None
    error_code: Optional[str] = None

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0
        return round((self.processed / self.total) * 100, 1)

    def to_dict(self):
        return {
            "total": self.total,
            "processed": self.processed,
            "percent": self.percent,
            "status": self.status,
            "action": self.action,
            "error": self.error,
            "error_code": self.error_code,
        }


class GmailService:
    """
    Core Gmail service using IMAP + App Password.
    All operations use IMAP UIDs for stable email identification.
    Fetch/delete run as background tasks, browser just reads state.
    """

    def __init__(self):
        self._mail: Optional[imaplib.IMAP4_SSL] = None
        self._email_address: str = ""
        self._app_password: str = ""
        self._lock_code: str = ""
        self._selected_folder: Optional[str] = None
        self.progress = ActionProgress()
        # Initialize DB layer
        db.init_db()
        self._bg_task: Optional[asyncio.Task] = None

    # ── Session persistence ──────────────────────────────────────

    def _save_session(self):
        """Save credentials to disk so login survives restart."""
        db.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "email": self._email_address,
            "token": base64.b64encode(self._app_password.encode()).decode(),
            "lock_code": self._lock_code
        }
        SESSION_FILE.write_text(json.dumps(data))

    def _load_session(self) -> bool:
        """Try to restore session from disk. Returns True if successful."""
        if not SESSION_FILE.exists():
            return False
        try:
            data = json.loads(SESSION_FILE.read_text())
            email_addr = data["email"]
            app_pass = base64.b64decode(data["token"]).decode()
            lock_code = data.get("lock_code", "")
            self.authenticate(email_addr, app_pass, lock_code, save=False)
            return True
        except Exception:
            # Session file corrupted or credentials expired
            logger.warning("Failed to restore session, clearing session file")
            SESSION_FILE.unlink(missing_ok=True)
            return False

    def _clear_session(self):
        SESSION_FILE.unlink(missing_ok=True)

    # ── Authentication ───────────────────────────────────────────

    def is_authenticated(self) -> bool:
        return self._mail is not None and self._email_address != ""

    def try_restore(self) -> bool:
        """Try to restore a saved session on startup. Returns True if logged in."""
        if self.is_authenticated():
            return True
        return self._load_session()

    def authenticate(self, email_address: str, app_password: str, lock_code: str = "", save: bool = True) -> bool:
        """Connect to Gmail IMAP. Persists session if save=True."""
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(email_address, app_password)
            self._mail = mail
            self._email_address = email_address
            self._app_password = app_password
            self._lock_code = lock_code
            if save:
                self._save_session()
            return True
        except imaplib.IMAP4.error as e:
            raise ValueError(f"Login failed: {e}. Check your email and app password.")

    def _reconnect(self):
        """Reconnect if the IMAP connection dropped."""
        try:
            self._mail.noop()
        except Exception:
            if not self._email_address or not self._app_password:
                raise ConnectionError("Cannot reconnect: no credentials available")
            self._mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            self._mail.login(self._email_address, self._app_password)

    def get_profile(self) -> dict:
        return {"email": self._email_address}

    def verify_lock(self, code: str) -> bool:
        return code == self._lock_code

    def logout(self):
        """Disconnect, cancel background tasks, clear session."""
        self._cancel_bg_task()
        if self._mail:
            try:
                self._mail.logout()
            except Exception:
                pass
        self._mail = None
        self._email_address = ""
        self._app_password = ""
        self._lock_code = ""
        self._selected_folder = None
        self.progress = ActionProgress()
        self._clear_session()
        db.clear_db()

    # ── Folder selection ─────────────────────────────────────────

    @staticmethod
    def _select_folder_on_connection(mail, candidates, readonly=True):
        """Try each candidate folder on a given IMAP connection. Returns the folder name or None."""
        for folder in candidates:
            try:
                status, _ = mail.select(folder, readonly)
                if status == "OK":
                    return folder
            except Exception:
                continue
        return None

    def _select_folder(self, readonly: bool = True) -> bool:
        """Select All Mail (or INBOX) folder. Caches the name."""
        self._reconnect()
        if self._selected_folder:
            try:
                status, _ = self._mail.select(self._selected_folder, readonly)
                if status == "OK":
                    return True
            except Exception:
                pass

        folder = self._select_folder_on_connection(self._mail, FOLDER_CANDIDATES, readonly)
        if folder:
            self._selected_folder = folder
            return True
        return False

    # ── Background task management ───────────────────────────────

    def _cancel_bg_task(self):
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
            self._bg_task = None

    def _handle_bg_error(self, e: Exception, context: str = ""):
        """Central error handling mechanism for IMAP Background Tasks."""
        self.progress.status = "error"
        err_msg = str(e).lower()
        if isinstance(e, imaplib.IMAP4.error) or "connection" in err_msg or "timeout" in err_msg or "socket" in err_msg:
            self.progress.error_code = "NETWORK_ERROR"
            self.progress.error = f"Network/Connection dropped during {context}. Please check your connection."
        elif "login" in err_msg or "auth" in err_msg or "credential" in err_msg:
            self.progress.error_code = "AUTH_ERROR"
            self.progress.error = f"Authentication failed during {context}. Credentials may have expired."
        elif "limit" in err_msg or "bandwidth" in err_msg:
            self.progress.error_code = "IMAP_LIMIT"
            self.progress.error = f"Gmail IMAP bandwidth limit exceeded during {context}. Please wait."
        else:
            self.progress.error_code = "UNKNOWN_ERROR"
            self.progress.error = f"An unexpected error occurred during {context}: {str(e)}"
        logger.error("Background task error during %s: %s", context, e)

    def is_busy(self) -> bool:
        return self._bg_task is not None and not self._bg_task.done()

    # ── Email parsing ────────────────────────────────────────────

    def _parse_uid_message(self, uid_str: str, msg_data: bytes, flags_data: bytes) -> EmailHeader:
        """Parse a raw email into EmailHeader using UID as identifier."""
        msg = email.message_from_bytes(msg_data)

        raw_from = decode_header_value(msg.get("From", ""))
        sender_name, sender_email = email.utils.parseaddr(raw_from)
        if not sender_name:
            sender_name = sender_email.split("@")[0] if sender_email else "Unknown"

        subject = decode_header_value(msg.get("Subject", "(No Subject)"))

        raw_date = msg.get("Date", "")
        try:
            parsed = email.utils.parsedate_to_datetime(raw_date)
            timestamp = parsed.timestamp()
            date_str = parsed.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp = 0
            date_str = raw_date

        flags_str = flags_data.decode("utf-8", errors="replace") if isinstance(flags_data, bytes) else str(flags_data)
        is_read = "\\Seen" in flags_str

        return EmailHeader(
            uid=uid_str,
            subject=subject,
            sender_email=sender_email,
            sender_name=sender_name,
            date=date_str,
            timestamp=timestamp,
            is_read=is_read,
        )

    # ── Shared fetch response parser ─────────────────────────────

    def _parse_fetch_response(self, response):
        """Parse an IMAP UID FETCH response and append to self.emails."""
        parsed_emails = []
        j = 0
        while j < len(response):
            item = response[j]
            if isinstance(item, tuple) and len(item) == 2:
                meta_line = item[0]
                header_data = item[1]
                meta_str = meta_line.decode("utf-8", errors="replace")

                uid_str = ""
                if "UID " in meta_str:
                    uid_start = meta_str.index("UID ") + 4
                    uid_end = meta_str.index(" ", uid_start) if " " in meta_str[uid_start:] else len(meta_str)
                    uid_str = meta_str[uid_start:uid_end].strip().rstrip(")")
                
                if not uid_str:
                    j += 1
                    continue

                flags_part = b""
                if b"FLAGS" in meta_line:
                    start = meta_line.find(b"FLAGS (")
                    if start != -1:
                        end = meta_line.find(b")", start + 7)
                        flags_part = meta_line[start : end + 1]

                try:
                    parsed = self._parse_uid_message(uid_str, header_data, flags_part)
                    parsed_emails.append(parsed)
                except Exception:
                    logger.warning("Failed to parse email UID=%s, skipping", uid_str)
            j += 1
        return parsed_emails

    # ── Fetch: parallelized ──────────────────────────────────────

    def start_full_fetch(self, batch_size: int = 200):
        """Launch a full fetch as a background task."""
        self._cancel_bg_task()
        self._bg_task = asyncio.create_task(self._do_full_fetch(batch_size))

    def start_refresh(self, batch_size: int = 200):
        """Launch an incremental fetch as a background task."""
        if self.is_busy():
            return
        self._cancel_bg_task()
        self._bg_task = asyncio.create_task(self._do_refresh(batch_size))

    async def _fetch_worker_task(self, uids: list[bytes], batch_size: int, worker_id: int):
        """Worker task that uses its own IMAP connection to fetch a subset of emails."""
        mail = None
        try:
            # Create a dedicated connection for this worker
            mail = await asyncio.to_thread(imaplib.IMAP4_SSL, IMAP_HOST, IMAP_PORT)
            await asyncio.to_thread(mail.login, self._email_address, self._app_password)
            
            # Select folder (read-only) using shared helper
            selected = await asyncio.to_thread(
                self._select_folder_on_connection, mail, FOLDER_CANDIDATES, True
            )
            if not selected:
                return []

            worker_emails = []
            for i in range(0, len(uids), batch_size):
                batch = uids[i : i + batch_size]
                uid_range = b",".join(batch)

                status, response = await asyncio.to_thread(
                    mail.uid, "FETCH", uid_range,
                    "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
                )
                if status != "OK":
                    continue

                batch_emails = self._parse_fetch_response(response)
                
                if batch_emails:
                    db.insert_emails(batch_emails)

                self.progress.processed += len(batch_emails)
                await asyncio.sleep(0.01)

        finally:
            if mail:
                try:
                    await asyncio.to_thread(mail.logout)
                except Exception:
                    pass

    async def _do_fetch_uids(self, uids: list[bytes], batch_size: int, context: str):
        """Shared: fetch given UIDs using parallel workers."""
        self.progress.total = len(uids)
        self.progress.processed = 0
        self.progress.status = "fetching"

        chunk_size = (len(uids) + NUM_WORKERS - 1) // NUM_WORKERS
        chunks = [uids[i : i + chunk_size] for i in range(0, len(uids), chunk_size)]

        tasks = [
            self._fetch_worker_task(chunk, batch_size, i)
            for i, chunk in enumerate(chunks)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Fetch worker %d failed: %s", i, result)

        self.progress.status = "done"

    async def _do_full_fetch(self, batch_size: int):
        """Background: fetch all email headers using parallel workers."""
        self.progress = ActionProgress(status="discovering", action="fetch")

        try:
            ok = await asyncio.to_thread(self._select_folder, True)
            if not ok:
                self.progress.status = "error"
                self.progress.error = "Could not open mailbox folder"
                return

            status, data = await asyncio.to_thread(self._mail.uid, "SEARCH", None, "ALL")
            if status != "OK":
                self.progress.status = "error"
                self.progress.error = "Failed to search mailbox"
                return

            uid_list = data[0].split()
            if not uid_list:
                self.progress.status = "done"
                return

            await self._do_fetch_uids(uid_list, batch_size, "full fetch")

        except asyncio.CancelledError:
            self.progress.status = "idle"
        except Exception as e:
            self._handle_bg_error(e, "full fetch")

    async def _do_refresh(self, batch_size: int):
        """Background: fetch only emails not already cached using parallel workers."""
        self.progress = ActionProgress(status="discovering", action="fetch")

        try:
            ok = await asyncio.to_thread(self._select_folder, True)
            if not ok:
                self.progress.status = "error"
                self.progress.error = "Could not open mailbox folder"
                return

            status, data = await asyncio.to_thread(self._mail.uid, "SEARCH", None, "ALL")
            if status != "OK":
                self.progress.status = "error"
                self.progress.error = "Failed to search mailbox"
                return

            all_uids = data[0].split()
            with db.get_connection() as conn:
                rows = conn.execute("SELECT uid FROM emails").fetchall()
                known_uids = {row["uid"] for row in rows}

            new_uids = [u for u in all_uids if u.decode("utf-8", errors="replace") not in known_uids]

            if not new_uids:
                self.progress = ActionProgress(total=0, processed=0, status="done", action="fetch")
                return

            await self._do_fetch_uids(new_uids, batch_size, "incremental refresh")

        except asyncio.CancelledError:
            self.progress.status = "idle"
        except Exception as e:
            self._handle_bg_error(e, "incremental refresh")

    # ── Delete operations ────────────────────────────────────────

    def start_delete(self, uids: list[str], batch_size: int = 50):
        """Launch delete as a background task using UIDs."""
        self._cancel_bg_task()
        self._bg_task = asyncio.create_task(self._do_delete(uids, batch_size))

    def start_delete_by_sender(self, sender_email: str):
        """Delete all cached emails from a specific sender."""
        with db.get_connection() as conn:
            rows = conn.execute("SELECT uid FROM emails WHERE LOWER(sender_email) = ?", (sender_email.lower(),)).fetchall()
            uids = [r["uid"] for r in rows]
        if not uids:
            self.progress = ActionProgress(status="done", action="delete")
            return
        self.start_delete(uids)

    def start_bulk_delete_by_senders(self, sender_emails: list[str]):
        """Delete all cached emails from multiple specific senders."""
        if not sender_emails:
            self.progress = ActionProgress(status="done", action="delete")
            return
        placeholders = ",".join("?" for _ in sender_emails)
        with db.get_connection() as conn:
            rows = conn.execute(f"SELECT uid FROM emails WHERE LOWER(sender_email) IN ({placeholders})", [e.lower() for e in sender_emails]).fetchall()
            uids = [r["uid"] for r in rows]
        if not uids:
            self.progress = ActionProgress(status="done", action="delete")
            return
        self.start_delete(uids)

    async def _do_delete(self, uids: list[str], batch_size: int = 50):
        """Background: delete emails by UID — move to Trash."""
        self.progress = ActionProgress(
            total=len(uids),
            status="deleting",
            action="delete",
        )

        try:
            ok = await asyncio.to_thread(self._select_folder, False)  # read-write
            if not ok:
                self.progress.status = "error"
                self.progress.error = "Could not open mailbox for deletion"
                return

            deleted_uids = set()

            for i in range(0, len(uids), batch_size):
                batch = uids[i : i + batch_size]
                uid_range = ",".join(batch)

                # Copy to Trash then mark deleted
                copied = False
                for trash in TRASH_CANDIDATES:
                    try:
                        status, _ = await asyncio.to_thread(
                            self._mail.uid, "COPY", uid_range, trash
                        )
                        if status == "OK":
                            copied = True
                            break
                    except Exception:
                        continue

                if copied:
                    await asyncio.to_thread(
                        self._mail.uid, "STORE", uid_range, "+FLAGS", "(\\Deleted)"
                    )
                    await asyncio.to_thread(self._mail.expunge)
                    deleted_uids.update(batch)

                self.progress.processed = len(deleted_uids)
                await asyncio.sleep(0.05)

            # Remove from local cache
            if deleted_uids:
                placeholders = ",".join("?" for _ in deleted_uids)
                with db.get_connection() as conn:
                    conn.execute(f"DELETE FROM emails WHERE uid IN ({placeholders})", list(deleted_uids))
                    conn.commit()

            self.progress.status = "done"

        except asyncio.CancelledError:
            self.progress.status = "idle"
        except Exception as e:
            self._handle_bg_error(e, "delete operation")

    # ── Query helpers ────────────────────────────────────────────

    def get_emails(self) -> list[dict]:
        with db.get_connection() as conn:
            return conn.execute("SELECT * FROM emails").fetchall()

    def search_emails(self, query: str) -> list[dict]:
        q = f"%{query}%"
        with db.get_connection() as conn:
            return conn.execute(
                "SELECT * FROM emails WHERE subject LIKE ? OR sender_name LIKE ? OR sender_email LIKE ?",
                (q, q, q)
            ).fetchall()

    def get_sender_stats(self, search: str = "") -> list[dict]:
        with db.get_connection() as conn:
            query = '''
                SELECT 
                    sender_email, 
                    MAX(sender_name) as sender_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_read = 1 THEN 1 ELSE 0 END) as read,
                    SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) as unread,
                    MAX(date) as latest_date,
                    MAX(timestamp) as latest_timestamp
                FROM emails 
            '''
            params = ()
            if search:
                query += " WHERE sender_name LIKE ? OR sender_email LIKE ? "
                q = f"%{search}%"
                params = (q, q)
                
            query += '''
                GROUP BY LOWER(sender_email)
                ORDER BY total DESC
            '''
            rows = conn.execute(query, params).fetchall()
            return rows

    def get_summary(self) -> dict:
        with db.get_connection() as conn:
            row = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_read = 1 THEN 1 ELSE 0 END) as read,
                    COUNT(DISTINCT LOWER(sender_email)) as unique_senders
                FROM emails
            ''').fetchone()
            
            total = row["total"] or 0
            read = row["read"] or 0
            return {
                "total": total,
                "read": read,
                "unread": total - read,
                "unique_senders": row["unique_senders"] or 0,
            }
