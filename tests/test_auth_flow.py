

def test_register_and_login(client):
    # Step 1: Register a new user
    register_payload = {"email": "testuser@example.com", "password": "secret123"}
    resp = client.post("/api/v1/auth/register", json=register_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data.get("email") == "testuser@example.com"
    assert data.get("id") is not None

    # Step 2: Log in with the new user credentials
    login_payload = {"username": "testuser@example.com", "password": "secret123"}
    resp = client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    login_data = resp.json()
    assert "access_token" in login_data
    assert login_data.get("token_type") == "bearer"
    # return the token for further tests
    token = login_data["access_token"]
    return token

def test_create_and_list_organisations(client):
    # First log in to get a valid token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser@example.com", "password": "secret123"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Create a new organisation
    org_name = "My Test Org"
    create_resp = client.post(
        "/api/v1/organisations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": org_name},
    )
    assert create_resp.status_code == 200
    org_data = create_resp.json()
    assert org_data.get("name") == org_name
    org_pid = org_data.get("pid")
    assert isinstance(org_pid, str) and len(org_pid) > 0

    # List organisations and verify the new org is present
    list_resp = client.get(
        "/api/v1/organisations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    orgs = list_resp.json()
    assert any(o.get("pid") == org_pid and o.get("name") == org_name for o in orgs)
