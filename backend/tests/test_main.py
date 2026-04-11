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
