import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import pool

from app.main import app
from app.database import Base, get_db
from app.dependencies.auth import create_access_token

TEST_DATABASE_URL = "postgresql+asyncpg://agrisense:agrisense@localhost:5432/agrisense_test"

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=pool.NullPool)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def farmer_token():
    return create_access_token({"user_id": 1, "role": "farmer"})


@pytest.fixture
def buyer_token():
    return create_access_token({"user_id": 2, "role": "buyer"})


@pytest.fixture
def fpo_admin_token():
    return create_access_token({"user_id": 3, "role": "fpo_admin"})
