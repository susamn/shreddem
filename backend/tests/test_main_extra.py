import pytest
import asyncio
from unittest.mock import MagicMock, patch
from main import app, lifespan, gmail

@pytest.mark.asyncio
async def test_lifespan():
    with patch.object(gmail, "try_restore", return_value=True) as mock_restore:
        async with lifespan(app):
            mock_restore.assert_called_once()
        # Test cleanup part of lifespan
        # (Though there's not much visible side effect to check easily)
