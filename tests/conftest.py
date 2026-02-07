import os
import pytest

@pytest.fixture(autouse=True)
def force_mock_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock-1")