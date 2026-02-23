"""Tests for auth routes."""
import json


def test_register_new_user(client):
    resp = client.post("/api/auth/register", json={
        "display_name": "TestUser",
        "email": "test@example.com",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "registered"
    assert "password" in data
    assert data["user"]["email"] == "test@example.com"


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json={
        "display_name": "User1",
        "email": "dup@example.com",
    })
    resp = client.post("/api/auth/register", json={
        "display_name": "User2",
        "email": "dup@example.com",
    })
    assert resp.status_code == 409
    assert "already registered" in resp.get_json()["error"]


def test_login_valid(client):
    reg = client.post("/api/auth/register", json={
        "display_name": "LoginUser",
        "email": "login@example.com",
    })
    password = reg.get_json()["password"]
    resp = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": password,
    })
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "login@example.com"


def test_login_invalid_password(client):
    client.post("/api/auth/register", json={
        "display_name": "BadLogin",
        "email": "bad@example.com",
    })
    resp = client.post("/api/auth/login", json={
        "email": "bad@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


def test_me_unauthenticated(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.get_json()["authenticated"] is False


def test_register_missing_fields(client):
    resp = client.post("/api/auth/register", json={"display_name": ""})
    assert resp.status_code == 400


def test_logout(client):
    reg = client.post("/api/auth/register", json={
        "display_name": "LogoutUser",
        "email": "logout@example.com",
    })
    password = reg.get_json()["password"]
    client.post("/api/auth/login", json={
        "email": "logout@example.com",
        "password": password,
    })
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "logged_out"
