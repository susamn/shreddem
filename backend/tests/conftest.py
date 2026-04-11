import pytest
from unittest.mock import MagicMock, patch
from gmail_service import GmailService
import db

@pytest.fixture
def mock_imap():
    with patch("imaplib.IMAP4_SSL") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_instance.login.return_value = ("OK", [b"Logged in"])
        mock_instance.select.return_value = ("OK", [b"OK"])
        yield mock_instance

@pytest.fixture
def gmail_service(mock_imap):
    # Ensure a fresh database for every test
    db.clear_db()
    
    service = GmailService()
    service._mail = mock_imap
    service._email_address = "test@gmail.com"
    service._app_password = "test_password"
    # Reset internal state
    service._selected_folder = None
    return service

def insert_test_emails(emails: list):
    """Helper to inject test emails directly into the DB."""
    with db.get_connection() as conn:
        for em in emails:
            if hasattr(em, "to_dict"):
                conn.execute(
                    "INSERT OR REPLACE INTO emails (uid, subject, sender_email, sender_name, date, timestamp, is_read, snippet) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (em.uid, em.subject, em.sender_email, 
                     em.sender_name, em.date, em.timestamp, 
                     int(em.is_read), getattr(em, "snippet", ""))
                )
            elif isinstance(em, dict):
                # For dictionaries
                conn.execute(
                    "INSERT OR REPLACE INTO emails (uid, subject, sender_email, sender_name, date, timestamp, is_read, snippet) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (em.get("uid"), em.get("subject", ""), em.get("sender_email", ""), 
                     em.get("sender_name", ""), em.get("date", ""), em.get("timestamp", 0), 
                     int(em.get("is_read", True)), em.get("snippet", ""))
                )
        conn.commit()
