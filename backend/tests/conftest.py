import pytest
from unittest.mock import MagicMock, patch
from gmail_service import GmailService

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
    # Ensure a fresh instance for every test
    service = GmailService()
    service._mail = mock_imap
    service._email_address = "test@gmail.com"
    service._app_password = "test_password"
    # Reset internal state
    service.emails = []
    service._known_uids = set()
    service._selected_folder = None
    return service
