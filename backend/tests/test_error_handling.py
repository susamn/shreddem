"""
Tests for error handling, edge cases, and previously uncovered code paths
in gmail_service.py.
"""
import pytest
import imaplib
from unittest.mock import MagicMock, patch
from gmail_service import (
    GmailService, EmailHeader, ActionProgress,
    decode_header_value, FOLDER_CANDIDATES, TRASH_CANDIDATES,
)
from conftest import insert_test_emails


# ── ActionProgress tests ─────────────────────────────────────────

class TestActionProgress:
    def test_percent_zero_total(self):
        p = ActionProgress(total=0, processed=0)
        assert p.percent == 0

    def test_percent_partial(self):
        p = ActionProgress(total=200, processed=100)
        assert p.percent == 50.0

    def test_percent_complete(self):
        p = ActionProgress(total=10, processed=10)
        assert p.percent == 100.0

    def test_to_dict_includes_all_fields(self):
        p = ActionProgress(total=5, processed=2, status="fetching", action="fetch", error="oops", error_code="NETWORK_ERROR")
        d = p.to_dict()
        assert d["total"] == 5
        assert d["processed"] == 2
        assert d["percent"] == 40.0
        assert d["status"] == "fetching"
        assert d["action"] == "fetch"
        assert d["error"] == "oops"
        assert d["error_code"] == "NETWORK_ERROR"

    def test_to_dict_defaults(self):
        p = ActionProgress()
        d = p.to_dict()
        assert d["status"] == "idle"
        assert d["error"] is None
        assert d["error_code"] is None


# ── _handle_bg_error classification tests ────────────────────────

class TestHandleBgError:
    def test_network_error_imap(self, gmail_service):
        gmail_service._handle_bg_error(imaplib.IMAP4.error("connection reset"), "fetch")
        assert gmail_service.progress.error_code == "NETWORK_ERROR"
        assert gmail_service.progress.status == "error"

    def test_network_error_timeout(self, gmail_service):
        gmail_service._handle_bg_error(Exception("socket timeout occurred"), "fetch")
        assert gmail_service.progress.error_code == "NETWORK_ERROR"

    def test_network_error_connection(self, gmail_service):
        gmail_service._handle_bg_error(Exception("Connection refused"), "fetch")
        assert gmail_service.progress.error_code == "NETWORK_ERROR"

    def test_auth_error(self, gmail_service):
        gmail_service._handle_bg_error(Exception("login credentials invalid"), "fetch")
        assert gmail_service.progress.error_code == "AUTH_ERROR"

    def test_auth_error_variant(self, gmail_service):
        gmail_service._handle_bg_error(Exception("Authentication required"), "fetch")
        assert gmail_service.progress.error_code == "AUTH_ERROR"

    def test_imap_limit_error(self, gmail_service):
        gmail_service._handle_bg_error(Exception("bandwidth limit exceeded"), "fetch")
        assert gmail_service.progress.error_code == "IMAP_LIMIT"

    def test_unknown_error(self, gmail_service):
        gmail_service._handle_bg_error(Exception("something weird"), "fetch")
        assert gmail_service.progress.error_code == "UNKNOWN_ERROR"
        assert "something weird" in gmail_service.progress.error

    def test_context_in_message(self, gmail_service):
        gmail_service._handle_bg_error(Exception("oops"), "full fetch")
        assert "full fetch" in gmail_service.progress.error


# ── verify_lock / get_profile tests ──────────────────────────────

class TestSimpleMethods:
    def test_verify_lock_success(self, gmail_service):
        gmail_service._lock_code = "1234"
        assert gmail_service.verify_lock("1234") is True

    def test_verify_lock_failure(self, gmail_service):
        gmail_service._lock_code = "1234"
        assert gmail_service.verify_lock("wrong") is False

    def test_verify_lock_empty(self, gmail_service):
        gmail_service._lock_code = ""
        assert gmail_service.verify_lock("") is True

    def test_get_profile(self, gmail_service):
        gmail_service._email_address = "me@example.com"
        assert gmail_service.get_profile() == {"email": "me@example.com"}

    def test_is_busy_no_task(self, gmail_service):
        gmail_service._bg_task = None
        assert gmail_service.is_busy() is False

    def test_is_busy_done_task(self, gmail_service):
        mock_task = MagicMock()
        mock_task.done.return_value = True
        gmail_service._bg_task = mock_task
        assert gmail_service.is_busy() is False

    def test_is_busy_running_task(self, gmail_service):
        mock_task = MagicMock()
        mock_task.done.return_value = False
        gmail_service._bg_task = mock_task
        assert gmail_service.is_busy() is True

    def test_is_authenticated(self, gmail_service):
        assert gmail_service.is_authenticated() is True
        gmail_service._mail = None
        assert gmail_service.is_authenticated() is False

    def test_is_authenticated_empty_email(self, gmail_service):
        gmail_service._email_address = ""
        assert gmail_service.is_authenticated() is False


# ── Email parsing edge cases ─────────────────────────────────────

class TestParseEdgeCases:
    def test_parse_uid_message_no_subject(self, gmail_service):
        msg_data = b"From: sender@example.com\r\nDate: Mon, 1 Jan 2024 10:00:00 +0000\r\n\r\n"
        flags_data = b""
        header = gmail_service._parse_uid_message("1", msg_data, flags_data)
        assert header.subject == "(No Subject)"

    def test_parse_uid_message_bad_date(self, gmail_service):
        msg_data = b"From: sender@example.com\r\nSubject: Test\r\nDate: not-a-date\r\n\r\n"
        flags_data = b""
        header = gmail_service._parse_uid_message("1", msg_data, flags_data)
        assert header.timestamp == 0
        assert header.date == "not-a-date"

    def test_parse_uid_message_no_sender(self, gmail_service):
        msg_data = b"Subject: Test\r\nDate: Mon, 1 Jan 2024 10:00:00 +0000\r\n\r\n"
        flags_data = b""
        header = gmail_service._parse_uid_message("1", msg_data, flags_data)
        assert header.sender_name == "Unknown"
        assert header.sender_email == ""

    def test_parse_uid_message_unread(self, gmail_service):
        msg_data = b"From: a@b.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 10:00:00 +0000\r\n\r\n"
        flags_data = b"()"
        header = gmail_service._parse_uid_message("1", msg_data, flags_data)
        assert header.is_read is False

    def test_parse_uid_message_flags_as_string(self, gmail_service):
        msg_data = b"From: a@b.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 10:00:00 +0000\r\n\r\n"
        flags_data = "(\\Seen)"  # string, not bytes
        header = gmail_service._parse_uid_message("1", msg_data, flags_data)
        assert header.is_read is True


# ── decode_header_value edge cases ───────────────────────────────

class TestDecodeHeader:
    def test_empty_string(self):
        assert decode_header_value("") == ""

    def test_none_like(self):
        assert decode_header_value(None) == ""

    def test_plain_ascii(self):
        assert decode_header_value("Hello World") == "Hello World"


# ── get_sender_stats with search ─────────────────────────────────

class TestSenderStats:
    def test_sender_stats_with_search(self, gmail_service):
        insert_test_emails([
            EmailHeader(uid="1", subject="S1", sender_email="alice@example.com", sender_name="Alice", date="", timestamp=1, is_read=True),
            EmailHeader(uid="2", subject="S2", sender_email="bob@example.com", sender_name="Bob", date="", timestamp=2, is_read=False),
        ])
        stats = gmail_service.get_sender_stats(search="alice")
        assert len(stats) == 1
        assert stats[0]["sender_email"] == "alice@example.com"

    def test_sender_stats_search_no_results(self, gmail_service):
        insert_test_emails([
            EmailHeader(uid="1", subject="S1", sender_email="alice@example.com", sender_name="Alice", date="", timestamp=1, is_read=True),
        ])
        stats = gmail_service.get_sender_stats(search="zzz_nonexistent")
        assert len(stats) == 0


# ── Delete edge cases ────────────────────────────────────────────

class TestDeleteEdgeCases:
    @pytest.mark.asyncio
    async def test_do_delete_all_trash_fail(self, gmail_service):
        """When no trash folder is found, emails stay but operation completes."""
        insert_test_emails([
            EmailHeader(uid="1", subject="S", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True),
        ])
        # All COPY attempts fail
        gmail_service._mail.uid.side_effect = Exception("No trash")
        
        with patch.object(gmail_service, "_select_folder", return_value=True):
            await gmail_service._do_delete(["1"])
        
        # Operation completes (status=done) but email wasn't actually deleted from local cache
        # because no COPY succeeded (deleted_uids is empty)
        assert gmail_service.progress.status == "done"

    def test_start_delete_by_sender_no_matches(self, gmail_service):
        gmail_service.start_delete_by_sender("nonexistent@example.com")
        assert gmail_service.progress.status == "done"
        assert gmail_service.progress.action == "delete"

    def test_start_bulk_delete_empty_list(self, gmail_service):
        gmail_service.start_bulk_delete_by_senders([])
        assert gmail_service.progress.status == "done"
        assert gmail_service.progress.action == "delete"

    def test_start_bulk_delete_no_matching_senders(self, gmail_service):
        insert_test_emails([
            EmailHeader(uid="1", subject="S", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True),
        ])
        gmail_service.start_bulk_delete_by_senders(["nonexistent@example.com"])
        assert gmail_service.progress.status == "done"


# ── Fetch edge cases ────────────────────────────────────────────

class TestFetchEdgeCases:
    @pytest.mark.asyncio
    async def test_do_full_fetch_folder_fail(self, gmail_service):
        with patch.object(gmail_service, "_select_folder", return_value=False):
            await gmail_service._do_full_fetch(batch_size=200)
        assert gmail_service.progress.status == "error"
        assert "mailbox folder" in gmail_service.progress.error

    @pytest.mark.asyncio
    async def test_do_full_fetch_search_fail(self, gmail_service):
        gmail_service._mail.uid.return_value = ("NO", [b"error"])
        with patch.object(gmail_service, "_select_folder", return_value=True):
            await gmail_service._do_full_fetch(batch_size=200)
        assert gmail_service.progress.status == "error"
        assert "search" in gmail_service.progress.error.lower()

    @pytest.mark.asyncio
    async def test_do_full_fetch_empty_mailbox(self, gmail_service):
        gmail_service._mail.uid.return_value = ("OK", [b""])
        with patch.object(gmail_service, "_select_folder", return_value=True):
            await gmail_service._do_full_fetch(batch_size=200)
        assert gmail_service.progress.status == "done"

    @pytest.mark.asyncio
    async def test_do_refresh_no_new_emails(self, gmail_service):
        insert_test_emails([
            EmailHeader(uid="1", subject="S", sender_email="a@b.com", sender_name="A", date="", timestamp=1, is_read=True),
        ])
        gmail_service._mail.uid.return_value = ("OK", [b"1"])
        with patch.object(gmail_service, "_select_folder", return_value=True):
            await gmail_service._do_refresh(batch_size=200)
        assert gmail_service.progress.status == "done"
        assert gmail_service.progress.total == 0

    @pytest.mark.asyncio
    async def test_do_delete_folder_fail(self, gmail_service):
        with patch.object(gmail_service, "_select_folder", return_value=False):
            await gmail_service._do_delete(["1"])
        assert gmail_service.progress.status == "error"
        assert "mailbox" in gmail_service.progress.error.lower()


# ── _select_folder_on_connection tests ───────────────────────────

class TestSelectFolderOnConnection:
    def test_success(self):
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"OK"])
        result = GmailService._select_folder_on_connection(mock_mail, FOLDER_CANDIDATES)
        assert result == '"[Gmail]/All Mail"'

    def test_all_fail(self):
        mock_mail = MagicMock()
        mock_mail.select.side_effect = Exception("Fail")
        result = GmailService._select_folder_on_connection(mock_mail, FOLDER_CANDIDATES)
        assert result is None

    def test_second_candidate(self):
        mock_mail = MagicMock()
        mock_mail.select.side_effect = [("NO", [b"err"]), ("OK", [b"OK"])]
        result = GmailService._select_folder_on_connection(mock_mail, FOLDER_CANDIDATES)
        assert result == '"[Gmail]/Tous les messages"'


# ── Reconnect edge cases ────────────────────────────────────────

class TestReconnectEdgeCases:
    def test_reconnect_no_credentials(self, gmail_service):
        gmail_service._mail.noop.side_effect = Exception("Disconnected")
        gmail_service._email_address = ""
        gmail_service._app_password = ""
        with pytest.raises(ConnectionError, match="no credentials"):
            gmail_service._reconnect()


# ── Module constants ─────────────────────────────────────────────

class TestModuleConstants:
    def test_folder_candidates_not_empty(self):
        assert len(FOLDER_CANDIDATES) > 0

    def test_trash_candidates_not_empty(self):
        assert len(TRASH_CANDIDATES) > 0

    def test_inbox_in_folder_candidates(self):
        assert "INBOX" in FOLDER_CANDIDATES
