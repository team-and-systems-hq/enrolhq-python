"""Shared fixtures for tests."""

import pytest

from enrolhq import EnrolHQClient


@pytest.fixture(scope="session")
def client():
    """Create a client from .env credentials (session-scoped to reuse auth)."""
    return EnrolHQClient()
