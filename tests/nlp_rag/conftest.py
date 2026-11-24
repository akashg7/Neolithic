"""Offline NLP / RAG / eval tests.

The repo-wide tests/conftest.py has an autouse `setup_db` fixture that needs a
live Postgres. These tests never touch the database (translation, units,
lexicon, chunker and retriever all run offline with stubs / in-memory Qdrant),
so we override that fixture with a no-op for this directory only.
"""
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield
