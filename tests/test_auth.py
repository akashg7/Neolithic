import pytest


@pytest.mark.asyncio
async def test_register_farmer(client):
    """Test farmer registration returns 201 with token."""
    response = await client.post("/auth/register", json={
        "name": "Test Farmer",
        "phone": "9999999999",
        "password": "test123456",
        "role": "farmer",
        "lat": 28.6139,
        "lng": 77.2090,
    })
    assert response.status_code == 201
    data = response.json()
    assert "token" in data
    assert data["user"]["role"] == "farmer"
    assert data["user"]["phone"] == "9999999999"


@pytest.mark.asyncio
async def test_register_buyer(client):
    """Test buyer registration returns 201 with token."""
    response = await client.post("/auth/register", json={
        "name": "Test Buyer",
        "phone": "8888888888",
        "password": "test123456",
        "role": "buyer",
        "company_name": "AgriCorp Foods",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["role"] == "buyer"


@pytest.mark.asyncio
async def test_register_duplicate_phone(client):
    """Test duplicate phone number returns 409."""
    payload = {
        "name": "Farmer One",
        "phone": "7777777777",
        "password": "test123456",
        "role": "farmer",
    }
    await client.post("/auth/register", json=payload)
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    """Test login with correct credentials returns 200 with token."""
    # Register first
    await client.post("/auth/register", json={
        "name": "Login Test",
        "phone": "6666666666",
        "password": "test123456",
        "role": "farmer",
    })

    # Login
    response = await client.post("/auth/login", json={
        "phone": "6666666666",
        "password": "test123456",
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Test login with wrong password returns 401."""
    await client.post("/auth/register", json={
        "name": "Wrong Pass Test",
        "phone": "5555555555",
        "password": "correctpassword",
        "role": "farmer",
    })

    response = await client.post("/auth/login", json={
        "phone": "5555555555",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client):
    """Test /users/me with valid token returns user profile."""
    reg = await client.post("/auth/register", json={
        "name": "Me Test",
        "phone": "4444444444",
        "password": "test123456",
        "role": "farmer",
    })
    token = reg.json()["token"]

    response = await client.get("/users/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Me Test"
    assert data["role"] == "farmer"


@pytest.mark.asyncio
async def test_get_me_no_token(client):
    """Test /users/me without token returns 403."""
    response = await client.get("/users/me")
    assert response.status_code == 403
