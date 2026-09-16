import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.config import settings

client = TestClient(app)


def test_github_webhook_ping_event():
    """Verify that GitHub 'ping' events return HTTP 200 with {'message': 'pong', 'status': 'ok'}."""
    # Test /api/webhook/github
    res1 = client.post(
        "/api/webhook/github",
        json={"zen": "Non-blocking is better than blocking."},
        headers={"X-GitHub-Event": "ping"},
    )
    assert res1.status_code == status.HTTP_200_OK
    assert res1.json() == {"message": "pong", "status": "ok"}

    # Test alias route /webhook/github
    res2 = client.post(
        "/webhook/github",
        json={"zen": "Design for failure."},
        headers={"X-GitHub-Event": "ping"},
    )
    assert res2.status_code == status.HTTP_200_OK
    assert res2.json() == {"message": "pong", "status": "ok"}


def test_github_webhook_unconfigured_secret_allows_testing():
    """Verify that when GITHUB_WEBHOOK_SECRET is empty/placeholder, delivery is allowed without 401."""
    payload = {
        "action": "synchronize",
        "pull_request": {
            "number": 99,
            "title": "Autonomous test PR",
            "head": {"ref": "patch-test", "sha": "c0ffee99"},
            "base": {"ref": "main"},
        },
        "repository": {"full_name": "tcet-opensource/quantum-core"},
    }

    res = client.post(
        "/api/webhook/github",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == {"detail": "Webhook received"}


def test_github_webhook_hmac_raw_body_verification(monkeypatch):
    """Verify that HMAC SHA-256 matches exact raw request body bytes when secret is configured."""
    test_secret = "test_custom_webhook_secret_456"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", test_secret)

    raw_body = b'{"action": "synchronize", "pull_request": {"number": 101, "title": "Raw Bytes PR", "head": {"ref": "test", "sha": "123"}, "base": {"ref": "main"}}, "repository": {"full_name": "org/repo"}}'
    
    # 1. Without signature -> rejected with 401
    res_no_sig = client.post(
        "/api/webhook/github",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-GitHub-Event": "pull_request"},
    )
    assert res_no_sig.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. With wrong signature -> rejected with 401
    res_wrong_sig = client.post(
        "/api/webhook/github",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalidhash00000000000000000000000000000000000000000000000000000000",
        },
    )
    assert res_wrong_sig.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. With correct HMAC on raw body bytes -> accepted with 200 OK
    computed_mac = hmac.new(test_secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
    valid_sig = f"sha256={computed_mac}"

    res_valid = client.post(
        "/api/webhook/github",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": valid_sig,
        },
    )
    assert res_valid.status_code == status.HTTP_200_OK
    assert res_valid.json() == {"detail": "Webhook received"}
