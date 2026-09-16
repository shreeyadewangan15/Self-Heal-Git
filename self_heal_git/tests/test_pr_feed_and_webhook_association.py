import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlmodel import Session, select

from app.config import engine
from app.models import User, UserRole, Repository, PRRecord
from app.auth import create_access_token
from app.main import app

client = TestClient(app)


@pytest.fixture
def db_feed_and_webhook_setup():
    """Seed test users, repositories, and PRs."""
    with Session(engine) as session:
        # 1. Admin user
        admin = User(
            email="shreeya.tcet@gmail.com",
            full_name="Shreeya Admin",
            role=UserRole.ADMIN,
            auth_provider="google",
            is_active=True,
        )
        # 2. Developer user (standard user)
        dev = User(
            email="developer_alice@tcetmumbai.in",
            full_name="Alice Developer",
            role=UserRole.DEVELOPER,
            auth_provider="google",
            is_active=True,
        )
        # 3. Another developer user
        other_dev = User(
            email="developer_bob@gmail.com",
            full_name="Bob Developer",
            role=UserRole.DEVELOPER,
            auth_provider="google",
            is_active=True,
        )
        session.add(admin)
        session.add(dev)
        session.add(other_dev)
        session.commit()
        session.refresh(admin)
        session.refresh(dev)
        session.refresh(other_dev)

        # Alice's repository
        alice_repo = Repository(
            full_name="alice-org/algo-lib",
            webhook_secret="whsec_alice",
            is_active=True,
            auto_commit_enabled=True,
            created_by_id=dev.id,
        )
        # Bob's repository
        bob_repo = Repository(
            full_name="bob-org/payment-service",
            webhook_secret="whsec_bob",
            is_active=True,
            auto_commit_enabled=True,
            created_by_id=other_dev.id,
        )
        session.add(alice_repo)
        session.add(bob_repo)
        session.commit()
        session.refresh(alice_repo)
        session.refresh(bob_repo)

        # 1. PR assigned to Alice
        pr_alice = PRRecord(
            repo="alice-org/algo-lib",
            pr_number=10,
            title="Alice PR Fix binary search",
            status="ANALYZING",
            user_id=dev.id,
            repo_id=alice_repo.id,
        )
        # 2. PR assigned to Bob
        pr_bob = PRRecord(
            repo="bob-org/payment-service",
            pr_number=20,
            title="Bob PR Fix stripe gateway",
            status="HEALED",
            user_id=other_dev.id,
            repo_id=bob_repo.id,
        )
        # 3. Unassigned PR (user_id IS NULL)
        pr_unassigned = PRRecord(
            repo="monitored-community/public-lib",
            pr_number=30,
            title="Community unassigned PR",
            status="RECEIVED",
            user_id=None,
            repo_id=None,
        )
        # 4. PR in Alice's repo, but user_id was set to another author or None
        pr_in_alice_repo = PRRecord(
            repo="alice-org/algo-lib",
            pr_number=11,
            title="External contributor to Alice repo",
            status="ANALYZING",
            user_id=None,
            repo_id=alice_repo.id,
        )
        session.add(pr_alice)
        session.add(pr_bob)
        session.add(pr_unassigned)
        session.add(pr_in_alice_repo)
        session.commit()

        admin_token = create_access_token({"sub": admin.email, "role": admin.role.value, "user_id": admin.id})
        dev_token = create_access_token({"sub": dev.email, "role": dev.role.value, "user_id": dev.id})
        other_dev_token = create_access_token({"sub": other_dev.email, "role": other_dev.role.value, "user_id": other_dev.id})

        data = {
            "admin_id": admin.id,
            "dev_id": dev.id,
            "other_dev_id": other_dev.id,
            "admin_token": admin_token,
            "dev_token": dev_token,
            "other_dev_token": other_dev_token,
            "pr_alice_id": pr_alice.id,
            "pr_bob_id": pr_bob.id,
            "pr_unassigned_id": pr_unassigned.id,
            "pr_in_alice_repo_id": pr_in_alice_repo.id,
        }

    yield data

    # Teardown
    with Session(engine) as session:
        for p in session.exec(select(PRRecord)).all():
            session.delete(p)
        for r in session.exec(select(Repository)).all():
            session.delete(r)
        for u in session.exec(select(User).where(User.email.in_([
            "shreeya.tcet@gmail.com",
            "developer_alice@tcetmumbai.in",
            "developer_bob@gmail.com",
            "shreeyadewangan15@gmail.com",
        ]))).all():
            session.delete(u)
        session.commit()


def test_standard_developer_feed_filtering(db_feed_and_webhook_setup):
    """Verify that a standard user (DEVELOPER) sees:
    - PRs where pr.user_id == current_user.id
    - PRs where pr.repo matches repository belonging to user
    - PRs where pr.user_id IS NULL (unassigned incoming PRs from monitored repos)
    - But DOES NOT see PRs belonging to other users in other repos.
    """
    data = db_feed_and_webhook_setup

    # Test GET /api/prs/my-feed
    res = client.get(
        "/api/prs/my-feed",
        headers={"Authorization": f"Bearer {data['dev_token']}"},
    )
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    returned_pr_ids = [p["id"] for p in body["prs"]]

    assert data["pr_alice_id"] in returned_pr_ids  # pr.user_id == current_user.id
    assert data["pr_in_alice_repo_id"] in returned_pr_ids  # pr.repo matches user repo
    assert data["pr_unassigned_id"] in returned_pr_ids  # pr.user_id IS NULL
    assert data["pr_bob_id"] not in returned_pr_ids  # other user's PR in other repo

    # Test GET /api/prs (compat endpoint with bearer token)
    res_prs = client.get(
        "/api/prs",
        headers={"Authorization": f"Bearer {data['dev_token']}"},
    )
    assert res_prs.status_code == status.HTTP_200_OK
    body_prs = res_prs.json()
    returned_compat_ids = [p["id"] for p in body_prs["prs"]]

    assert data["pr_alice_id"] in returned_compat_ids
    assert data["pr_in_alice_repo_id"] in returned_compat_ids
    assert data["pr_unassigned_id"] in returned_compat_ids
    assert data["pr_bob_id"] not in returned_compat_ids


def test_admin_feed_returns_all_prs(db_feed_and_webhook_setup):
    """Verify that ADMIN user receives ALL PRs regardless of user_id or repository ownership."""
    data = db_feed_and_webhook_setup

    res = client.get(
        "/api/prs/my-feed",
        headers={"Authorization": f"Bearer {data['admin_token']}"},
    )
    assert res.status_code == status.HTTP_200_OK
    body = res.json()
    returned_pr_ids = [p["id"] for p in body["prs"]]

    assert data["pr_alice_id"] in returned_pr_ids
    assert data["pr_bob_id"] in returned_pr_ids
    assert data["pr_unassigned_id"] in returned_pr_ids
    assert data["pr_in_alice_repo_id"] in returned_pr_ids


def test_webhook_ingestion_user_association(db_feed_and_webhook_setup):
    """Verify that incoming GitHub webhook matches PR by author login or email and assigns user_id."""
    data = db_feed_and_webhook_setup

    # 1. Ingest PR with author login matching Alice
    webhook_payload = {
        "action": "opened",
        "pull_request": {
            "number": 555,
            "title": "Fix memory leak in buffer",
            "user": {
                "login": "developer_alice",
                "email": "developer_alice@tcetmumbai.in",
            },
            "head": {"ref": "fix-leak", "sha": "abcdef123"},
            "base": {"ref": "main"},
        },
        "repository": {
            "full_name": "alice-org/algo-lib",
        },
    }

    res = client.post(
        "/api/webhook/github",
        json=webhook_payload,
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert res.status_code == status.HTTP_200_OK

    with Session(engine) as session:
        stored = session.exec(
            select(PRRecord).where(PRRecord.repo == "alice-org/algo-lib", PRRecord.pr_number == 555)
        ).first()
        assert stored is not None
        assert stored.user_id == data["dev_id"]  # matched to Alice


def test_webhook_ingestion_shreeyadewangan15_repository_visibility(db_feed_and_webhook_setup):
    """Verify newly ingested webhook records from shreeyadewangan15/Self-Heal-Git:
    - User is matched via username/email or assigned to default active user.
    - user_id is NOT left as NULL.
    - Visible in the dashboard to logged-in developer accounts.
    """
    data = db_feed_and_webhook_setup

    webhook_payload = {
        "action": "opened",
        "pull_request": {
            "number": 777,
            "title": "Autonomous healing PR from GitHub",
            "user": {
                "login": "shreeyadewangan15",
            },
            "head": {"ref": "patch-branch", "sha": "deadbeef99"},
            "base": {"ref": "main"},
        },
        "repository": {
            "full_name": "shreeyadewangan15/Self-Heal-Git",
        },
    }

    res = client.post(
        "/api/webhook/github",
        json=webhook_payload,
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert res.status_code == status.HTTP_200_OK

    with Session(engine) as session:
        pr_record = session.exec(
            select(PRRecord).where(
                PRRecord.repo == "shreeyadewangan15/Self-Heal-Git",
                PRRecord.pr_number == 777,
            )
        ).first()
        assert pr_record is not None
        # user_id must NOT be None
        assert pr_record.user_id is not None

    # Now verify Alice (standard developer) calls my-feed
    # If the PR was assigned to default active developer (Alice), or if unassigned, Alice can see it
    res_feed = client.get(
        "/api/prs/my-feed",
        headers={"Authorization": f"Bearer {data['dev_token']}"},
    )
    assert res_feed.status_code == status.HTTP_200_OK
    feed_body = res_feed.json()
    feed_pr_numbers = [p["pr_number"] for p in feed_body["prs"]]
    assert 777 in feed_pr_numbers
