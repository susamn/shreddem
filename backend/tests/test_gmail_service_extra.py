import pytest
import asyncio
import json
import base64
from unittest.mock import MagicMock, patch, ANY
import imaplib
from gmail_service import GmailService, EmailHeader, ActionProgress, SESSION_FILE, decode_header_value
from conftest import insert_test_emails

@pytest.mark.asyncio
async def test_select_folder_multiple_candidates(gmail_service):
    # First candidate fails, second succeeds
    gmail_service._mail.select.side_effect = [Exception("Fail"), ("OK", [b"OK"])]
    gmail_service._selected_folder = None
    assert gmail_service._select_folder() is True
    assert gmail_service._selected_folder == '"[Gmail]/Tous les messages"'

@pytest.mark.asyncio
async def test_do_delete_trash_rotation(gmail_service):
    insert_test_emails([EmailHeader(uid="1", subject="S", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True)])
    
    # First trash candidate fails, second succeeds
    gmail_service._mail.uid.side_effect = [
        Exception("Trash fail"), # COPY to candidate 1
        ("OK", [b"OK"]),        # COPY to candidate 2
        ("OK", [b"OK"]),        # STORE FLAGS
        ("OK", [b"OK"]),        # EXPUNGE
    ]
    
    with patch.object(gmail_service, "_select_folder", return_value=True):
        await gmail_service._do_delete(["1"])
    assert len(gmail_service.get_emails()) == 0

@pytest.mark.asyncio
async def test_fetch_worker_task_imap_fail(gmail_service):
    with patch("imaplib.IMAP4_SSL", side_effect=Exception("Connection error")):
        with pytest.raises(Exception, match="Connection error"):
            await gmail_service._fetch_worker_task([b"1"], batch_size=1, worker_id=0)

def test_email_header_to_dict():
    header = EmailHeader(uid="1", subject="S", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True)
    d = header.to_dict()
    assert d["uid"] == "1"
    assert d["subject"] == "S"

def test_decode_header_value_complex():
    assert decode_header_value("=?utf-8?b?VGVzdA==?=") == "Test"
    assert "Part1" in decode_header_value("Part1\r\nPart2")

@pytest.mark.asyncio
async def test_try_restore(gmail_service):
    with patch.object(gmail_service, "is_authenticated", return_value=False):
        with patch.object(gmail_service, "_load_session", return_value=True):
            assert gmail_service.try_restore() is True
    
    with patch.object(gmail_service, "is_authenticated", return_value=True):
        assert gmail_service.try_restore() is True

@pytest.mark.asyncio
async def test_session_load_fail(gmail_service):
    with patch("pathlib.Path.exists", return_value=False):
        assert gmail_service._load_session() is False

@pytest.mark.asyncio
async def test_reconnect_fail(gmail_service):
    gmail_service._mail.noop.side_effect = Exception("Fail")
    with patch("imaplib.IMAP4_SSL", side_effect=Exception("Major fail")):
        with pytest.raises(Exception, match="Major fail"):
            gmail_service._reconnect()

@pytest.mark.asyncio
async def test_load_session_corrupted(gmail_service):
    SESSION_FILE.write_text("not json")
    assert gmail_service._load_session() is False
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()

def test_cancel_bg_task(gmail_service):
    mock_task = MagicMock()
    mock_task.done.return_value = False
    gmail_service._bg_task = mock_task
    gmail_service._cancel_bg_task()
    mock_task.cancel.assert_called_once()
