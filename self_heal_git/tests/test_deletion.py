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
def db_users_and_data():
    """Seed test admin, developer 1, and developer 2 with repositories and PRs."""
    with Session(engine) as session:
        # Create Admin
        admin = User(
            email="admin_del_test@tcetmumbai.in",
            full_name="Admin Delete Tester",
            role=UserRole.ADMIN,
            auth_provider="google",
            is_active=True,
        )
        # Create Developer 1
        dev1 = User(
            email="dev1_del_test@gmail.com",
            full_name="Dev One",
            role=UserRole.DEVELOPER,
            auth_provider="google",
            is_active=True,
        )
        # Create Developer 2
        dev2 = User(
            email="dev2_del_test@gmail.com",
            full_name="Dev Two",
            role=UserRole.DEVELOPER,
            auth_provider="google",
            is_active=True,
        )
        session.add(admin)
        session.add(dev1)
        session.add(dev2)
        session.commit()
        session.refresh(admin)
        session.refresh(dev1)
        session.refresh(dev2)

        # Create a repo
        repo = Repository(
            full_name="tcet-opensource/test-repo-delete",
            webhook_secret="test_secret_123",
            is_active=True,
            auto_commit_enabled=True,
            created_by_id=admin.id,
        )
        session.add(repo)
        session.commit()
        session.refresh(repo)

        # Create PR owned by dev1
        pr_dev1 = PRRecord(
            repo="tcet-opensource/test-repo-delete",
            pr_number=101,
            title="Dev1 Fix issue",
            status="ANALYZING",
            user_id=dev1.id,
            repo_id=repo.id,
        )
        # Create PR owned by dev2
        pr_dev2 = PRRecord(
            repo="tcet-opensource/test-repo-delete",
            pr_number=102,
            title="Dev2 Feature update",
            status="HEALED",
            user_id=dev2.id,
            repo_id=repo.id,
        )
        session.add(pr_dev1)
        session.add(pr_dev2)
        session.commit()
        session.refresh(pr_dev1)
        session.refresh(pr_dev2)

        repo_id = repo.id
        pr_dev1_id = pr_dev1.id
        pr_dev2_id = pr_dev2.id

        admin_token = create_access_token({"sub": admin.email, "role": admin.role.value, "user_id": admin.id})
        dev1_token = create_access_token({"sub": dev1.email, "role": dev1.role.value, "user_id": dev1.id})
        dev2_token = create_access_token({"sub": dev2.email, "role": dev2.role.value, "user_id": dev2.id})

        data = {
            "repo_id": repo_id,
            "pr_dev1_id": pr_dev1_id,
            "pr_dev2_id": pr_dev2_id,
            "admin_token": admin_token,
            "dev1_token": dev1_token,
            "dev2_token": dev2_token,
        }

    yield data

    # Teardown
    with Session(engine) as session:
        for p in session.exec(select(PRRecord)).all():
            session.delete(p)
        for r in session.exec(select(Repository)).all():
            session.delete(r)
        for u in session.exec(select(User).where(User.email.contains("del_test"))).all():
            session.delete(u)
        session.commit()


def test_admin_can_delete_repository(db_users_and_data):
    """Admins can delete any monitored repository."""
    data = db_users_and_data
    repo_id = data["repo_id"]

    res = client.delete(
        f"/api/admin/repositories/{repo_id}",
        headers={"Authorization": f"Bearer {data['admin_token']}"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == repo_id
    assert "removed" in res.json()["message"]

    # Verify repository is gone from database
    with Session(engine) as session:
        assert session.get(Repository, repo_id) is None


def test_developer_cannot_delete_repository(db_users_and_data):
    """Non-admin developer receives 403 Forbidden when attempting to delete a repository."""
    data = db_users_and_data
    repo_id = data["repo_id"]

    res = client.delete(
        f"/api/admin/repositories/{repo_id}",
        headers={"Authorization": f"Bearer {data['dev1_token']}"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_developer_can_delete_own_pr(db_users_and_data):
    """Developer can delete a pull request record they own."""
    data = db_users_and_data
    pr_id = data["pr_dev1_id"]

    res = client.delete(
        f"/api/prs/{pr_id}",
        headers={"Authorization": f"Bearer {data['dev1_token']}"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == pr_id
    assert "deleted successfully" in res.json()["message"]

    # Verify PR is removed from database
    with Session(engine) as session:
        assert session.get(PRRecord, pr_id) is None


def test_developer_cannot_delete_other_user_pr(db_users_and_data):
    """Developer cannot delete a PR belonging to another user (403 Forbidden)."""
    data = db_users_and_data
    pr_id = data["pr_dev1_id"]  # owned by dev1

    # dev2 tries to delete dev1's PR
    res = client.delete(
        f"/api/prs/{pr_id}",
        headers={"Authorization": f"Bearer {data['dev2_token']}"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "Forbidden" in res.json()["detail"]

    # Verify PR still exists in database
    with Session(engine) as session:
        assert session.get(PRRecord, pr_id) is not None


def test_admin_can_delete_any_pr(db_users_and_data):
    """Admin has clearance to delete any PR record."""
    data = db_users_and_data
    pr_id = data["pr_dev2_id"]  # owned by dev2

    res = client.delete(
        f"/api/prs/{pr_id}",
        headers={"Authorization": f"Bearer {data['admin_token']}"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == pr_id

    # Verify PR is removed from database
    with Session(engine) as session:
        assert session.get(PRRecord, pr_id) is None


def test_delete_nonexistent_pr_returns_404(db_users_and_data):
    """Deleting a non-existent PR returns 404 Not Found."""
    data = db_users_and_data
    res = client.delete(
        "/api/prs/999999",
        headers={"Authorization": f"Bearer {data['admin_token']}"},
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND
