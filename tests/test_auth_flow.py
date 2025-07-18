

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
        "/api/v1/auth/organisations",
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

def test_create_app_and_list_apps_and_switch_token(client):
    # Log in and get token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser@example.com", "password": "secret123"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a new organisation
    org_resp = client.post(
        "/api/v1/auth/organisations",
        headers=headers,
        json={"name": "App Test Org"}
    )
    assert org_resp.status_code == 200
    org_pid = org_resp.json()["pid"]

    # Create a new app within that organisation
    app_name = "My Test App"
    create_app_resp = client.post(
        f"/api/v1/auth/organisations/{org_pid}/apps",
        headers=headers,
        json={"name": app_name},
    )
    assert create_app_resp.status_code == 200
    app_data = create_app_resp.json()
    assert app_data.get("name") == app_name
    app_pid = app_data.get("pid")
    assert isinstance(app_pid, str) and len(app_pid) > 0

    # List apps and verify the new app is present
    list_apps_resp = client.get(
        "/api/v1/auth/apps",
        headers=headers,
    )
    assert list_apps_resp.status_code == 200
    apps = list_apps_resp.json()
    assert any(a.get("pid") == app_pid and a.get("name") == app_name for a in apps)

    # Switch app token
    switch_resp = client.post(
        f"/api/v1/auth/token/app/{app_pid}",
        headers=headers,
    )
    assert switch_resp.status_code == 200
    switch_data = switch_resp.json()
    assert "access_token" in switch_data
    assert switch_data.get("token_type") == "bearer"
