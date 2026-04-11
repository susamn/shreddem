import pytest
from httpx import ASGITransport, AsyncClient
from main import app, gmail, _auto_pull_loop
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

@pytest.fixture
def mock_auth():
    with patch.object(gmail, "is_authenticated", return_value=True):
        yield

@pytest.mark.asyncio
async def test_auth_status_not_authenticated():
    with patch.object(gmail, "is_authenticated", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/auth/status")
        assert response.status_code == 200
        assert response.json() == {"authenticated": False}

@pytest.mark.asyncio
async def test_login_failure():
    with patch.object(gmail, "authenticate", side_effect=ValueError("Invalid creds")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/auth/login", json={"email": "e", "app_password": "p", "lock_code": "1234"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid creds"

@pytest.mark.asyncio
async def test_login_success():
    with patch.object(gmail, "authenticate", return_value=True):
        with patch.object(gmail, "get_profile", return_value={"email": "test@example.com"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/auth/login", json={"email": "test@example.com", "app_password": "pw", "lock_code": "1234"})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["profile"]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login_generic_exception():
    with patch.object(gmail, "authenticate", side_effect=RuntimeError("IMAP internal")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/auth/login", json={"email": "e", "app_password": "p", "lock_code": "1234"})
        assert response.status_code == 500
        # Should NOT leak the internal error details
        assert "IMAP internal" not in response.json()["detail"]
        assert "internal error" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_logout(mock_auth):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/auth/logout")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_start_fetch_busy(mock_auth):
    with patch.object(gmail, "is_busy", return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/emails/fetch")
        assert response.status_code == 200
        assert response.json()["started"] is False

@pytest.mark.asyncio
async def test_get_emails_search_and_sort(mock_auth):
    with patch.object(gmail, "search_emails", return_value=[{"uid": "1", "timestamp": 100, "subject": "test"}]) as mock_search:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/emails?search=test&sort_by=subject&sort_order=asc")
        assert response.status_code == 200
        mock_search.assert_called_with("test")

@pytest.mark.asyncio
async def test_get_senders(mock_auth):
    with patch.object(gmail, "get_sender_stats", return_value=[{"sender_name": "A", "total": 5}]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/emails/senders")
        assert response.status_code == 200
        assert len(response.json()["senders"]) == 1

@pytest.mark.asyncio
async def test_get_summary(mock_auth):
    with patch.object(gmail, "get_summary", return_value={"total": 10}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/emails/summary")
        assert response.status_code == 200
        assert response.json()["total"] == 10

@pytest.mark.asyncio
async def test_auto_pull_config(mock_auth):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # GET
        response = await ac.get("/api/auto-pull")
        assert response.status_code == 200
        
        # POST
        response = await ac.post("/api/auto-pull", json={"interval": 60})
        assert response.status_code == 200
        assert response.json()["interval"] == 60

@pytest.mark.asyncio
async def test_delete_bulk_senders(mock_auth):
    with patch.object(gmail, "is_busy", return_value=False):
        with patch.object(gmail, "start_bulk_delete_by_senders") as mock_del:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/emails/delete-bulk-senders", json={"sender_emails": ["a@b.com"]})
            assert response.status_code == 200
            mock_del.assert_called_once()

@pytest.mark.asyncio
async def test_auto_pull_loop_execution():
    with patch("main.auto_pull_interval", 0.01):
        with patch.object(gmail, "is_authenticated", return_value=True):
            with patch.object(gmail, "is_busy", return_value=False):
                with patch.object(gmail, "start_refresh") as mock_refresh:
                    task = asyncio.create_task(_auto_pull_loop())
                    await asyncio.sleep(0.02)
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    mock_refresh.assert_called()

@pytest.mark.asyncio
async def test_verify_lock_endpoint():
    with patch.object(gmail, "is_authenticated", return_value=True):
        with patch.object(gmail, "verify_lock", return_value=True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/auth/verify-lock", json={"lock_code": "1234"})
            assert response.status_code == 200
            assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_verify_lock_endpoint_fail():
    with patch.object(gmail, "is_authenticated", return_value=True):
        with patch.object(gmail, "verify_lock", return_value=False):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/auth/verify-lock", json={"lock_code": "wrong"})
            assert response.status_code == 401

@pytest.mark.asyncio
async def test_verify_lock_unauthenticated():
    with patch.object(gmail, "is_authenticated", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/auth/verify-lock", json={"lock_code": "1234"})
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_delete_by_sender_endpoint(mock_auth):
    with patch.object(gmail, "is_busy", return_value=False):
        with patch.object(gmail, "start_delete_by_sender") as mock_del:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/api/emails/delete-by-sender", json={"sender_email": "a@b.com"})
            assert response.status_code == 200
            assert response.json()["started"] is True
            mock_del.assert_called_with("a@b.com")

@pytest.mark.asyncio
async def test_get_progress():
    with patch.object(gmail.progress, "to_dict", return_value={"status": "idle", "total": 0, "processed": 0, "percent": 0, "action": "fetch", "error": None, "error_code": None}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/emails/progress")
        assert response.status_code == 200
        assert response.json()["status"] == "idle"

@pytest.mark.asyncio
async def test_get_emails_pagination(mock_auth):
    emails = [{"uid": str(i), "timestamp": i, "subject": f"S{i}", "sender_name": f"N{i}"} for i in range(5)]
    with patch.object(gmail, "get_emails", return_value=emails):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/emails?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3
        assert len(data["emails"]) == 2

@pytest.mark.asyncio
async def test_get_emails_page_beyond_total(mock_auth):
    emails = [{"uid": "1", "timestamp": 1, "subject": "S", "sender_name": "N"}]
    with patch.object(gmail, "get_emails", return_value=emails):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/emails?page=100&page_size=50")
        assert response.status_code == 200
        assert len(response.json()["emails"]) == 0

@pytest.mark.asyncio
async def test_auth_status_authenticated():
    with patch.object(gmail, "is_authenticated", return_value=True):
        with patch.object(gmail, "get_profile", return_value={"email": "me@test.com"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/api/auth/status")
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["profile"]["email"] == "me@test.com"
