import pytest
import asyncio
from unittest.mock import MagicMock, patch, ANY
import imaplib
from gmail_service import GmailService, EmailHeader, ActionProgress

@pytest.mark.asyncio
async def test_select_folder_success(gmail_service):
    gmail_service._mail.select.return_value = ("OK", [b"123"])
    assert gmail_service._select_folder() is True
    assert gmail_service._selected_folder == '"[Gmail]/All Mail"'

@pytest.mark.asyncio
async def test_select_folder_fail(gmail_service):
    gmail_service._mail.select.return_value = ("NO", [b"error"])
    gmail_service._selected_folder = None
    assert gmail_service._select_folder() is False

def test_parse_uid_message(gmail_service):
    msg_data = b"From: Sender <sender@example.com>\r\nSubject: Test Subject\r\nDate: Mon, 1 Jan 2024 10:00:00 +0000\r\n\r\nBody"
    flags_data = b"(\\Seen)"
    header = gmail_service._parse_uid_message("101", msg_data, flags_data)
    
    assert header.uid == "101"
    assert header.subject == "Test Subject"
    assert header.sender_email == "sender@example.com"
    assert header.is_read is True

@pytest.mark.asyncio
async def test_do_full_fetch(gmail_service):
    gmail_service._mail.uid.side_effect = [
        ("OK", [b"1 2"]), # SEARCH ALL
        ("OK", [ (b'1 (UID 1 FLAGS (\\Seen))', b'From: A\r\nSubject: S1\r\nDate: Mon, 1 Jan 2024 10:00:00 +0000\r\n\r\n') ]), # FETCH 1
        ("OK", [ (b'2 (UID 2 FLAGS ())', b'From: B\r\nSubject: S2\r\nDate: Mon, 1 Jan 2024 11:00:00 +0000\r\n\r\n') ]), # FETCH 2
    ]
    
    with patch.object(gmail_service, "_select_folder", return_value=True):
        await gmail_service._do_full_fetch(batch_size=1)
        
    assert len(gmail_service.emails) == 2
    assert gmail_service.progress.status == "done"

@pytest.mark.asyncio
async def test_do_refresh(gmail_service):
    gmail_service._known_uids = {"1"}
    gmail_service.emails = [EmailHeader(uid="1", subject="S1", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True)]
    
    gmail_service._mail.uid.side_effect = [
        ("OK", [b"1 2"]), # SEARCH ALL returns 1 and 2
        ("OK", [ (b'2 (UID 2 FLAGS ())', b'From: B\r\nSubject: S2\r\nDate: Mon, 1 Jan 2024 11:00:00 +0000\r\n\r\n') ]), # FETCH 2
    ]
    
    with patch.object(gmail_service, "_select_folder", return_value=True):
        await gmail_service._do_refresh(batch_size=1)
        
    assert len(gmail_service.emails) == 2
    assert "2" in gmail_service._known_uids

@pytest.mark.asyncio
async def test_do_delete(gmail_service):
    gmail_service.emails = [
        EmailHeader(uid="1", subject="S1", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True)
    ]
    gmail_service._known_uids = {"1"}
    gmail_service._mail.uid.return_value = ("OK", [b"OK"])
    
    with patch.object(gmail_service, "_select_folder", return_value=True):
        await gmail_service._do_delete(["1"])
        
    assert len(gmail_service.emails) == 0

def test_sender_stats(gmail_service):
    gmail_service.emails = [
        EmailHeader(uid="1", subject="S1", sender_email="a@b.com", sender_name="A", date="2024-01-01", timestamp=1, is_read=True),
        EmailHeader(uid="2", subject="S2", sender_email="a@b.com", sender_name="A", date="2024-01-02", timestamp=2, is_read=False)
    ]
    stats = gmail_service.get_sender_stats()
    assert len(stats) == 1
    assert stats[0]["total"] == 2
    assert stats[0]["unread"] == 1

def test_get_summary(gmail_service):
    gmail_service.emails = [
        EmailHeader(uid="1", subject="S1", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True),
        EmailHeader(uid="2", subject="S2", sender_email="b@b.com", sender_name="B", date="", timestamp=2, is_read=False)
    ]
    summary = gmail_service.get_summary()
    assert summary["total"] == 2
    assert summary["read"] == 1
    assert summary["unread"] == 1

@pytest.mark.asyncio
async def test_authenticate_error(mock_imap):
    with patch("imaplib.IMAP4_SSL") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_instance.login.side_effect = imaplib.IMAP4.error("Login failed")
        service = GmailService()
        with pytest.raises(ValueError, match="Login failed"):
            service.authenticate("test@gmail.com", "pw")

def test_search_emails(gmail_service):
    gmail_service.emails = [
        EmailHeader(uid="1", subject="Apple", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True),
        EmailHeader(uid="2", subject="Banana", sender_email="b@b.com", sender_name="B", date="", timestamp=2, is_read=False)
    ]
    results = gmail_service.search_emails("apple")
    assert len(results) == 1
    assert results[0]["subject"] == "Apple"

@pytest.mark.asyncio
async def test_bulk_delete_by_senders(gmail_service):
    gmail_service.emails = [
        EmailHeader(uid="1", subject="S1", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True),
        EmailHeader(uid="2", subject="S2", sender_email="b@b.com", sender_name="B", date="", timestamp=2, is_read=False)
    ]
    gmail_service._known_uids = {"1", "2"}
    
    with patch.object(gmail_service, "start_delete") as mock_start_delete:
        gmail_service.start_bulk_delete_by_senders(["a@b.com"])
        mock_start_delete.assert_called_with(["1"])

def test_logout(gmail_service):
    gmail_service.emails = [{"uid": "1"}]
    gmail_service.logout()
    assert gmail_service.emails == []
    assert gmail_service._email_address == ""

@pytest.mark.asyncio
async def test_reconnect(gmail_service):
    # Test successful NOOP
    gmail_service._mail.noop.return_value = ("OK", [b"OK"])
    gmail_service._reconnect()
    gmail_service._mail.noop.assert_called_once()
    
    # Test reconnection on error
    gmail_service._mail.noop.side_effect = Exception("Disconnected")
    with patch("imaplib.IMAP4_SSL") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        gmail_service._reconnect()
        mock_instance.login.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_worker_task(gmail_service):
    with patch("imaplib.IMAP4_SSL") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_instance.login.return_value = ("OK", [b"OK"])
        mock_instance.select.return_value = ("OK", [b"OK"])
        mock_instance.uid.return_value = ("OK", [ (b'1 (UID 1 FLAGS (\\Seen))', b'From: A\r\nSubject: S1\r\nDate: Mon, 1 Jan 2024 10:00:00 +0000\r\n\r\n') ])
        mock_instance.logout.return_value = ("OK", [b"OK"])

        emails = await gmail_service._fetch_worker_task([b"1"], batch_size=1, worker_id=0)
        assert len(emails) == 1
        assert emails[0].uid == "1"
