import pytest
from httpx import ASGITransport, AsyncClient
from main import app, gmail
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_unauthenticated_all_routes():
    with patch.object(gmail, "is_authenticated", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Valid payloads to avoid 422
            payloads = {
                "/api/emails/delete": {"uids": ["1"]},
                "/api/emails/delete-by-sender": {"sender_email": "a@b.com"},
                "/api/emails/delete-bulk-senders": {"sender_emails": ["a@b.com"]},
                "/api/auto-pull": {"interval": 60},
            }
            
            routes = [
                ("/api/emails", "GET"),
                ("/api/emails/senders", "GET"),
                ("/api/emails/summary", "GET"),
                ("/api/emails/fetch", "POST"),
                ("/api/emails/refresh", "POST"),
                ("/api/emails/delete", "POST"),
                ("/api/emails/delete-by-sender", "POST"),
                ("/api/emails/delete-bulk-senders", "POST"),
            ]
            for route, method in routes:
                if method == "GET":
                    response = await ac.get(route)
                else:
                    response = await ac.post(route, json=payloads.get(route, {}))
                assert response.status_code == 401

@pytest.mark.asyncio
async def test_all_is_busy_routes():
    with patch.object(gmail, "is_authenticated", return_value=True):
        with patch.object(gmail, "is_busy", return_value=True):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                payloads = {
                    "/api/emails/delete": {"uids": ["1"]},
                    "/api/emails/delete-by-sender": {"sender_email": "a@b.com"},
                    "/api/emails/delete-bulk-senders": {"sender_emails": ["a@b.com"]},
                }
                routes = [
                    ("/api/emails/fetch", "POST"),
                    ("/api/emails/refresh", "POST"),
                    ("/api/emails/delete", "POST"),
                    ("/api/emails/delete-by-sender", "POST"),
                    ("/api/emails/delete-bulk-senders", "POST"),
                ]
                for route, method in routes:
                    response = await ac.post(route, json=payloads.get(route, {}))
                    assert response.status_code == 200
                    assert response.json()["started"] is False
