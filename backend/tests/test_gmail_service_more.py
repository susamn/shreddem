import pytest
import asyncio
import json
import base64
from unittest.mock import MagicMock, patch, ANY
import imaplib
from gmail_service import GmailService, EmailHeader, ActionProgress, SESSION_FILE, decode_header_value

@pytest.mark.asyncio
async def test_select_folder_already_selected(gmail_service):
    gmail_service._selected_folder = "INBOX"
    gmail_service._mail.select.return_value = ("OK", [b"OK"])
    assert gmail_service._select_folder() is True
    gmail_service._mail.select.assert_called_with("INBOX", ANY)

def test_parse_fetch_response_edge_cases(gmail_service):
    response = [
        "not a tuple",
        (b'no uid here', b'headers'),
        (b'UID 10 FLAGS (\\Seen)', b'From: A\r\nSubject: S\r\nDate: Mon, 1 Jan 2024 10:00:00 +0000\r\n\r\n')
    ]
    emails = gmail_service._parse_fetch_response(response)
    assert len(emails) == 1
    assert emails[0].uid == "10"

@pytest.mark.asyncio
async def test_do_delete_exception_outer(gmail_service):
    from conftest import insert_test_emails
    insert_test_emails([EmailHeader(uid="99", subject="S", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True)])
    
    # Mock _select_folder to raise Exception to trigger outer block
    with patch.object(gmail_service, "_select_folder", side_effect=Exception("Outer fail")):
        await gmail_service._do_delete(["99"])
    
    assert gmail_service.progress.status == "error"
    assert gmail_service.progress.error == "Outer fail"

@pytest.mark.asyncio
async def test_fetch_worker_task_no_folder(gmail_service):
    with patch("imaplib.IMAP4_SSL") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_instance.login.return_value = ("OK", [b"OK"])
        mock_instance.select.return_value = ("NO", [b"Fail"])
        emails = await gmail_service._fetch_worker_task([b"1"], batch_size=1, worker_id=0)
        assert emails == []

@pytest.mark.asyncio
async def test_load_session_success(gmail_service):
    data = {"email": "a@b.com", "token": base64.b64encode(b"pw").decode()}
    SESSION_FILE.write_text(json.dumps(data))
    
    with patch.object(gmail_service, "authenticate") as mock_auth:
        assert gmail_service._load_session() is True
        mock_auth.assert_called_with("a@b.com", "pw", "", save=False)
    
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
