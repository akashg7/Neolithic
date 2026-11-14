"""Member 1 — Factory, OTP expiry/throttle, Repository CRUD, polymorphic user roles.

These tests need no Postgres. Because services depend on repository
*interfaces* (DIP), every test injects in-memory repositories. The one
SQLAlchemy test uses in-memory SQLite and is skipped if `aiosqlite` is absent.
"""
from datetime import datetime, timedelta, timezone
from itertools import count
from typing import Optional, Sequence

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.dependencies.auth import create_access_token
from app.dependencies.repositories import (
    get_fpo_repository,
    get_otp_repository,
    get_user_repository,
)
from app.domain.factories.user_factory import ProfileCreator, UserFactory
from app.models.fpo import FPO
from app.models.otp import OtpCode
from app.models.user import Buyer, Farmer, User
from app.repositories.base import (
    IReadRepository,
    IRepository,
    IWriteRepository,
    SQLAlchemyBaseRepository,
)
from app.repositories.fpo_repository import IFpoRepository
from app.repositories.otp_repository import IOtpRepository
from app.repositories.user_repository import IUserRepository
from app.routers import auth as auth_router
from app.routers import fpo as fpo_router
from app.schemas.auth import RegisterRequest
from app.services.auth_service import AuthService, OtpService


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Override conftest's Postgres create/drop: this module uses in-memory repos."""
    yield


# ── In-memory repositories (test doubles for the repository interfaces) ──────

class InMemoryRepo(IRepository):
    def __init__(self):
        self.rows: dict[int, object] = {}
        self._ids = count(1)
        self.commits = 0

    async def get_by_id(self, id: int):
        return self.rows.get(id)

    async def list(self, skip: int = 0, limit: int = 100):
        return list(self.rows.values())[skip:skip + limit]

    async def create(self, entity):
        if getattr(entity, "id", None) is None:
            entity.id = next(self._ids)
        self.rows[entity.id] = entity
        return entity

    async def update(self, entity):
        self.rows[entity.id] = entity
        return entity

    async def delete(self, id: int) -> bool:
        return self.rows.pop(id, None) is not None

    async def commit(self) -> None:
        self.commits += 1


class InMemoryUserRepo(InMemoryRepo, IUserRepository):
    def __init__(self):
        super().__init__()
        self.profiles: list = []

    async def create(self, entity: User) -> User:
        entity.verified = bool(entity.verified)
        return await super().create(entity)

    async def get_by_phone(self, phone: str) -> Optional[User]:
        return next((u for u in self.rows.values() if u.phone == phone), None)

    async def get_with_profiles(self, user_id: int) -> Optional[User]:
        return self.rows.get(user_id)

    async def add_profile(self, profile):
        self.profiles.append(profile)
        return profile


class InMemoryOtpRepo(InMemoryRepo, IOtpRepository):
    async def latest_for_phone(self, phone: str) -> Optional[OtpCode]:
        rows = [o for o in self.rows.values() if o.phone == phone]
        return max(rows, key=lambda o: (o.created_at, o.id)) if rows else None

    async def count_issued_since(self, phone: str, since: datetime) -> int:
        return sum(1 for o in self.rows.values() if o.phone == phone and o.created_at >= since)

    async def delete_for_phone(self, phone: str) -> None:
        self.rows = {k: o for k, o in self.rows.items() if o.phone != phone}

    async def delete_issued_before(self, phone: str, before: datetime) -> None:
        self.rows = {k: o for k, o in self.rows.items() if not (o.phone == phone and o.created_at < before)}


class InMemoryFpoRepo(InMemoryRepo, IFpoRepository):
    def __init__(self, user_repo: InMemoryUserRepo):
        super().__init__()
        self.user_repo = user_repo

    def _farmers(self) -> list[Farmer]:
        return [p for p in self.user_repo.profiles if isinstance(p, Farmer)]

    async def get_fpo_id_for_user(self, user_id: int) -> Optional[int]:
        return next((f.fpo_id for f in self._farmers() if f.user_id == user_id), None)

    async def list_farmers(self, fpo_id: int) -> Sequence[Farmer]:
        return [f for f in self._farmers() if f.fpo_id == fpo_id]


@pytest.fixture
def repos():
    users = InMemoryUserRepo()
    otps = InMemoryOtpRepo()
    fpos = InMemoryFpoRepo(users)
    return users, otps, fpos


@pytest.fixture
def service(repos):
    users, otps, fpos = repos
    return AuthService(user_repo=users, otp_service=OtpService(otps), fpo_repo=fpos)


async def _register(service: AuthService, phone: str, role: str, **extra):
    code = await service.otp_service.issue(phone)
    return await service.register(RegisterRequest(
        name=extra.pop("name", f"User {phone}"), phone=phone, code=code, role=role, **extra
    ))


# ── 1. Factory Method Pattern ───────────────────────────────────────────────

def test_user_factory_creates_farmer():
    user = User(id=1, name="Ramesh", phone="9822011111", role="FARMER")
    farmer = UserFactory.create_user_profile(user, {"role": "farmer", "fpo_id": 7})
    assert isinstance(farmer, Farmer)
    assert farmer.user_id == 1
    assert farmer.fpo_id == 7
    assert farmer.user is user and user.farmer_profile is farmer


def test_user_factory_creates_buyer_and_keeps_only_gst_last4():
    user = User(id=2, name="Reliance Fresh", phone="9822022222", role="BUYER")
    buyer = UserFactory.create_user_profile(
        user, {"role": "buyer", "company_name": "Reliance Fresh", "gst_number": "27abcde1234f1z5"}
    )
    assert isinstance(buyer, Buyer)
    assert buyer.user_id == 2
    assert buyer.company_name == "Reliance Fresh"
    assert buyer.gst_last4 == "F1Z5"


def test_user_factory_fpo_admin_gets_farmer_profile():
    user = User(id=3, name="FPO Manager", phone="9822033333", role="FPO_ADMIN")
    assert isinstance(UserFactory.create_user_profile(user, {"role": "FPO_ADMIN"}), Farmer)


def test_user_factory_invalid_role_raises():
    user = User(id=4, phone="9822044444", role="invalid")
    with pytest.raises(ValueError):
        UserFactory.create_user_profile(user, {"role": "hacker"})


def test_user_factory_invalid_gst_raises():
    user = User(id=5, phone="9822055555", role="BUYER")
    with pytest.raises(ValueError):
        UserFactory.create_user_profile(user, {"role": "BUYER", "gst_number": "NOT-A-GSTIN"})


def test_user_factory_is_open_for_extension():
    """OCP: a new role plugs in without touching AuthService or the factory body."""
    class InspectorCreator(ProfileCreator):
        def create(self, user, payload):
            return Farmer(user_id=user.id)

    UserFactory.register("warehouse_inspector", InspectorCreator())
    try:
        assert "WAREHOUSE_INSPECTOR" in UserFactory.supported_roles()
        profile = UserFactory.create_user_profile(User(id=6), {"role": "warehouse_inspector"})
        assert profile.user_id == 6
    finally:
        UserFactory._creators.pop("WAREHOUSE_INSPECTOR")


# ── 2. Repository Pattern ───────────────────────────────────────────────────

def test_repository_interfaces_are_segregated():
    """ISP: read and write contracts are separate; IRepository composes both."""
    assert issubclass(IRepository, IReadRepository) and issubclass(IRepository, IWriteRepository)
    assert not issubclass(IReadRepository, IWriteRepository)
    assert {"get_by_id", "list"} <= IReadRepository.__abstractmethods__
    assert "create" not in IReadRepository.__abstractmethods__
    with pytest.raises(TypeError):
        IRepository()  # abstract


@pytest.mark.asyncio
async def test_sqlalchemy_base_repository_crud():
    pytest.importorskip("aiosqlite")
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # FPO + farmers only (users has a PostGIS column SQLite can't create;
        # SQLite doesn't enforce the dangling FK by default).
        await conn.run_sync(lambda c: (FPO.__table__.create(c), Farmer.__table__.create(c)))
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
        repo = SQLAlchemyBaseRepository(session, FPO)

        created = await repo.create(FPO(name="Sahyadri FPO", region="Nashik"))
        assert created.id is not None
        assert (await repo.get_by_id(created.id)).name == "Sahyadri FPO"

        created.region = "Nashik, MH"
        await repo.update(created)
        assert (await repo.get_by_id(created.id)).region == "Nashik, MH"

        await repo.create(FPO(name="MahaAgri FPO"))
        assert len(await repo.list()) == 2
        assert len(await repo.list(skip=1, limit=10)) == 1

        assert await repo.delete(created.id) is True
        assert await repo.delete(created.id) is False
        assert await repo.get_by_id(created.id) is None
    await engine.dispose()


# ── 3. OTP service: expiry, attempts, throttle ──────────────────────────────

@pytest.mark.asyncio
async def test_otp_issue_and_check(repos):
    _, otps, _ = repos
    svc = OtpService(otps)
    code = await svc.issue("9822011111")
    assert len(code) == 6 and code.isdigit()
    stored = await otps.latest_for_phone("9822011111")
    assert stored.code_hash != code  # hashed at rest
    wrong = "000000" if code != "000000" else "111111"
    assert await svc.check("9822011111", wrong) is False
    assert await svc.check("9822011111", code) is True


@pytest.mark.asyncio
async def test_otp_expired_code_rejected(repos):
    _, otps, _ = repos
    svc = OtpService(otps)
    code = await svc.issue("9822011111")
    (await otps.latest_for_phone("9822011111")).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert await svc.check("9822011111", code) is False


@pytest.mark.asyncio
async def test_otp_attempt_cap(repos):
    _, otps, _ = repos
    svc = OtpService(otps, max_attempts=5)
    code = await svc.issue("9822011111")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert await svc.check("9822011111", wrong) is False
    assert await svc.check("9822011111", code) is False  # locked out even with the right code


@pytest.mark.asyncio
async def test_otp_throttle_three_per_window(repos):
    _, otps, _ = repos
    svc = OtpService(otps, max_requests=3, window_seconds=600)
    for _ in range(3):
        await svc.issue("9822011111")
    with pytest.raises(HTTPException) as exc:
        await svc.issue("9822011111")
    assert exc.value.status_code == 429
    await svc.issue("9822099999")  # other phones unaffected

    # Once the window has passed, issuing is allowed again.
    for o in otps.rows.values():
        o.created_at -= timedelta(seconds=601)
    await svc.issue("9822011111")


@pytest.mark.asyncio
async def test_only_latest_otp_verifies(repos):
    _, otps, _ = repos
    svc = OtpService(otps)
    first = await svc.issue("9822011111")
    (await otps.latest_for_phone("9822011111")).created_at -= timedelta(seconds=5)
    second = await svc.issue("9822011111")
    if first != second:
        assert await svc.check("9822011111", first) is False
    assert await svc.check("9822011111", second) is True


# ── 4. AuthService: registration & login (polymorphic roles) ────────────────

@pytest.mark.asyncio
async def test_register_farmer_creates_user_and_profile(service, repos):
    users, otps, _ = repos
    res = await _register(service, "9822011111", "farmer", name="Ramesh")
    assert res.user.role == "FARMER" and res.token
    assert isinstance(users.profiles[0], Farmer)
    assert users.profiles[0].user_id == int(res.user.id)
    assert await otps.latest_for_phone("9822011111") is None  # OTP consumed


@pytest.mark.asyncio
async def test_register_buyer_creates_buyer_profile(service, repos):
    users, _, _ = repos
    res = await _register(service, "9822022222", "BUYER", company_name="AgriCorp", gst_number="27ABCDE1234F1Z5")
    assert res.user.role == "BUYER"
    assert isinstance(users.profiles[0], Buyer) and users.profiles[0].gst_last4 == "F1Z5"


@pytest.mark.asyncio
async def test_register_duplicate_phone_409(service):
    await _register(service, "9822011111", "FARMER")
    with pytest.raises(HTTPException) as exc:
        await _register(service, "9822011111", "FARMER")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_register_wrong_otp_401(service):
    await service.otp_service.issue("9822011111")
    with pytest.raises(HTTPException) as exc:
        await service.register(RegisterRequest(name="X", phone="9822011111", code="999999", role="FARMER"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_register_fpo_link_rules(service, repos):
    _, _, fpos = repos
    await fpos.create(FPO(id=1, name="Sahyadri"))

    with pytest.raises(HTTPException) as exc:  # admins can't self-claim an FPO
        await _register(service, "9822033333", "FPO_ADMIN", fpo_id=1)
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:  # unknown FPO
        await _register(service, "9822044444", "FARMER", fpo_id=99)
    assert exc.value.status_code == 400

    res = await _register(service, "9822055555", "FARMER", fpo_id=1)
    assert res.user.role == "FARMER"


@pytest.mark.asyncio
async def test_verify_otp_login(service):
    await _register(service, "9822011111", "FARMER")
    code = await service.otp_service.issue("9822011111")
    res = await service.verify_otp("9822011111", code)
    assert res.token and res.user.phone == "9822011111"


@pytest.mark.asyncio
async def test_verify_otp_unknown_user_404(service):
    code = await service.otp_service.issue("9822000000")
    with pytest.raises(HTTPException) as exc:
        await service.verify_otp("9822000000", code)
    assert exc.value.status_code == 404


# ── 5. HTTP API (routers wired to in-memory repos via dependency_overrides) ──

@pytest_asyncio.fixture
async def api(repos):
    users, otps, fpos = repos
    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api/v1/auth")
    app.include_router(fpo_router.farmers_router, prefix="/api/v1/fpo")
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_otp_repository] = lambda: otps
    app.dependency_overrides[get_fpo_repository] = lambda: fpos
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def _api_register(api, phone: str, role: str, **extra) -> dict:
    otp = (await api.post("/api/v1/auth/otp/request", json={"phone": phone})).json()
    res = await api.post("/api/v1/auth/register", json={
        "phone": phone, "code": otp["dev_otp"], "role": role, "name": f"User {phone}", **extra
    })
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_api_otp_request(api):
    res = await api.post("/api/v1/auth/otp/request", json={"phone": "9822011111"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True and body["message"] == "OTP sent"
    assert body["expires_in_s"] == 120 and len(body["dev_otp"]) == 6


@pytest.mark.asyncio
async def test_api_otp_request_throttled(api):
    for _ in range(3):
        assert (await api.post("/api/v1/auth/otp/request", json={"phone": "9822011111"})).status_code == 200
    assert (await api.post("/api/v1/auth/otp/request", json={"phone": "9822011111"})).status_code == 429


@pytest.mark.asyncio
async def test_api_register_verify_and_me(api):
    reg = await _api_register(api, "9822011111", "farmer")
    assert reg["user"]["role"] == "FARMER" and reg["token"] == reg["access_token"]

    otp = (await api.post("/api/v1/auth/otp/request", json={"phone": "9822011111"})).json()
    login = await api.post("/api/v1/auth/otp/verify", json={"phone": "9822011111", "code": otp["dev_otp"]})
    assert login.status_code == 200

    me = await api.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['token']}"})
    assert me.status_code == 200
    assert me.json()["user"]["phone"] == "9822011111"
    assert me.json()["user"]["farmer_profile"] is not None


@pytest.mark.asyncio
async def test_api_me_rejects_bad_token(api):
    res = await api.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_api_fpo_farmers_scoped_to_admins_fpo(api, repos):
    users, _, fpos = repos
    await fpos.create(FPO(id=1, name="Sahyadri"))
    await fpos.create(FPO(id=2, name="MahaAgri"))
    await _api_register(api, "9822011111", "FARMER", fpo_id=1)
    await _api_register(api, "9822012222", "FARMER", fpo_id=1)
    other = await _api_register(api, "9822013333", "FARMER", fpo_id=2)
    admin = await _api_register(api, "9822033333", "FPO_ADMIN")

    # Operator links the admin to FPO 1 (as scripts/seed_data.py does).
    next(p for p in users.profiles if p.user_id == int(admin["user"]["id"])).fpo_id = 1

    res = await api.get("/api/v1/fpo/farmers", headers={"Authorization": f"Bearer {admin['token']}"})
    assert res.status_code == 200
    phones = sorted(f["phone"] for f in res.json())
    assert phones == ["9822011111", "9822012222"]  # not FPO 2's farmer, not the admin

    # A farmer (wrong role) gets 404, not 403.
    res = await api.get("/api/v1/fpo/farmers", headers={"Authorization": f"Bearer {other['token']}"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_fpo_farmers_admin_without_fpo_404(api):
    admin = await _api_register(api, "9822033333", "FPO_ADMIN")
    res = await api.get("/api/v1/fpo/farmers", headers={"Authorization": f"Bearer {admin['token']}"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_token_role_claim_cannot_escalate(api):
    """Role comes from the DB row, not the JWT claim: a farmer forging role=FPO_ADMIN gets 404."""
    farmer = await _api_register(api, "9822011111", "FARMER")
    forged = create_access_token({"user_id": int(farmer["user"]["id"]), "role": "FPO_ADMIN"})
    res = await api.get("/api/v1/fpo/farmers", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 404
