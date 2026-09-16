import pytest
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, select

from app.config import engine, get_session
from app.models import User, UserRole, Repository, PRRecord, PRRun
from app.auth import get_current_user, require_role, hash_password, verify_password
from app.main import app


# Test router to verify require_role guard (prefixed without test_ to avoid pytest collection warning)
rbac_test_app = FastAPI()
rbac_test_app.include_router(app.router)

@rbac_test_app.get("/api/test/admin-only")
def admin_only_route(user: User = Depends(require_role([UserRole.ADMIN]))):
    return {"message": "Welcome Admin", "user": user.email}

@rbac_test_app.get("/api/test/developer-area")
def developer_area_route(user: User = Depends(require_role([UserRole.DEVELOPER, UserRole.ADMIN]))):
    return {"message": "Welcome Developer", "user": user.email}


@pytest.fixture(autouse=True)
def setup_test_db():
    """Reset database tables before each test for clean isolation."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


class TestAuthenticationAndRBAC:
    """Automated test suite verifying JWT Auth and Role-Based Access Control."""

    def test_password_hashing(self):
        """Verifies password hashing produces valid salted hashes and verifies cleanly."""
        raw_password = "SuperSecretPassword123!"
        hashed = hash_password(raw_password)

        assert hashed != raw_password
        assert verify_password(raw_password, hashed) is True
        assert verify_password("WrongPassword!", hashed) is False

    def test_registration_flow_and_role_assignment(self):
        """Verifies that the first registered user is ADMIN and subsequent users are DEVELOPER."""
        client = TestClient(app)

        # 1. First user registration -> ADMIN
        admin_payload = {
            "email": "chief_admin@selfheal.org",
            "password": "AdminPassword123!",
            "full_name": "Chief Administrator",
        }
        res_admin = client.post("/api/auth/register", json=admin_payload)
        assert res_admin.status_code == status.HTTP_201_CREATED
        admin_data = res_admin.json()
        assert admin_data["email"] == "chief_admin@selfheal.org"
        assert admin_data["role"] == "ADMIN"
        assert "hashed_password" not in admin_data

        # 2. Second user registration -> DEVELOPER
        dev_payload = {
            "email": "developer_jane@selfheal.org",
            "password": "DevPassword456!",
            "full_name": "Jane Developer",
        }
        res_dev = client.post("/api/auth/register", json=dev_payload)
        assert res_dev.status_code == status.HTTP_201_CREATED
        dev_data = res_dev.json()
        assert dev_data["email"] == "developer_jane@selfheal.org"
        assert dev_data["role"] == "DEVELOPER"

        # 3. Duplicate email rejection
        res_dup = client.post("/api/auth/register", json=admin_payload)
        assert res_dup.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in res_dup.json()["detail"]

    def test_login_and_jwt_generation(self):
        """Verifies authentication returns a valid bearer token and handles bad credentials."""
        client = TestClient(app)

        # Register a user
        client.post("/api/auth/register", json={
            "email": "user@selfheal.org",
            "password": "CorrectPassword123",
            "full_name": "Test User",
        })

        # Successful login
        res_login = client.post("/api/auth/login", json={
            "email": "user@selfheal.org",
            "password": "CorrectPassword123",
        })
        assert res_login.status_code == status.HTTP_200_OK
        login_data = res_login.json()
        assert "access_token" in login_data
        assert login_data["token_type"] == "bearer"
        assert login_data["email"] == "user@selfheal.org"
        assert login_data["role"] == "ADMIN"

        # Bad password
        res_bad_pw = client.post("/api/auth/login", json={
            "email": "user@selfheal.org",
            "password": "WrongPassword999",
        })
        assert res_bad_pw.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in res_bad_pw.json()["detail"]

        # Non-existent user
        res_bad_user = client.post("/api/auth/login", json={
            "email": "nobody@selfheal.org",
            "password": "AnyPassword",
        })
        assert res_bad_user.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_profile(self):
        """Verifies /api/auth/me requires valid bearer token and returns current profile."""
        client = TestClient(app)

        # Register user
        client.post("/api/auth/register", json={
            "email": "sarah@selfheal.org",
            "password": "Password789!",
            "full_name": "Sarah Connor",
        })

        # Login
        login_res = client.post("/api/auth/login", json={
            "email": "sarah@selfheal.org",
            "password": "Password789!",
        })
        token = login_res.json()["access_token"]

        # Access /api/auth/me with Bearer token
        res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == status.HTTP_200_OK
        me_data = res_me.json()
        assert me_data["email"] == "sarah@selfheal.org"
        assert me_data["full_name"] == "Sarah Connor"
        assert me_data["role"] == "ADMIN"

        # Unauthenticated request
        res_unauth = client.get("/api/auth/me")
        assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED

        # Tampered token
        res_tampered = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert res_tampered.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rbac_role_guard_enforcement(self):
        """Verifies that require_role grants access to authorized roles and denies unauthorized ones with HTTP 403."""
        client = TestClient(rbac_test_app)

        # 1. Register Admin (first user)
        admin_res = client.post("/api/auth/register", json={
            "email": "admin@tcet.org",
            "password": "AdminPassword123",
            "full_name": "System Admin",
        })
        admin_token = client.post("/api/auth/login", json={
            "email": "admin@tcet.org",
            "password": "AdminPassword123",
        }).json()["access_token"]

        # 2. Register Developer (second user)
        dev_res = client.post("/api/auth/register", json={
            "email": "dev@tcet.org",
            "password": "DevPassword123",
            "full_name": "Junior Developer",
        })
        dev_token = client.post("/api/auth/login", json={
            "email": "dev@tcet.org",
            "password": "DevPassword123",
        }).json()["access_token"]

        # 3. Test ADMIN route
        # Admin should succeed
        res_admin_ok = client.get("/api/test/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_admin_ok.status_code == status.HTTP_200_OK
        assert res_admin_ok.json()["user"] == "admin@tcet.org"

        # Developer should be forbidden (403)
        res_dev_forbidden = client.get("/api/test/admin-only", headers={"Authorization": f"Bearer {dev_token}"})
        assert res_dev_forbidden.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient role clearance" in res_dev_forbidden.json()["detail"]

        # 4. Test DEVELOPER route (allows DEVELOPER and ADMIN)
        res_dev_ok = client.get("/api/test/developer-area", headers={"Authorization": f"Bearer {dev_token}"})
        assert res_dev_ok.status_code == status.HTTP_200_OK

        res_admin_dev_ok = client.get("/api/test/developer-area", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_admin_dev_ok.status_code == status.HTTP_200_OK

    def test_repository_and_prrun_models(self):
        """Verifies Repository and PRRun/PRRecord foreign keys and model instantiation."""
        with Session(engine) as session:
            # Create user
            user = User(
                email="maintainer@tcet.org",
                hashed_password="hash",
                full_name="Repo Maintainer",
                role=UserRole.MAINTAINER,
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            # Create repository
            repo = Repository(
                full_name="tcet-opensource/quantum-core",
                webhook_secret="supersecret123",
                is_active=True,
                created_by_id=user.id,
            )
            session.add(repo)
            session.commit()
            session.refresh(repo)
            assert repo.id is not None
            assert repo.created_by_id == user.id

            # Create PRRun (aliased to PRRecord)
            pr_run = PRRun(
                repo=repo.full_name,
                pr_number=501,
                title="feat: add quantum entanglement module",
                status="HEALED",
                repo_id=repo.id,
                reviewed_by_id=user.id,
                confidence=0.98,
            )
            session.add(pr_run)
            session.commit()
            session.refresh(pr_run)

            assert pr_run.id is not None
            assert pr_run.repo_id == repo.id
            assert pr_run.reviewed_by_id == user.id

            # Verify querying PRRecord retrieves PRRun
            record = session.exec(select(PRRecord).where(PRRecord.id == pr_run.id)).first()
            assert record is not None
            assert record.repo_id == repo.id
            assert record.reviewed_by_id == user.id

    def test_google_auth_url_endpoint(self):
        """Verifies GET /api/auth/google/url returns valid Google OAuth2 authorization parameters."""
        client = TestClient(app)
        res = client.get("/api/auth/google/url")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "auth_url" in data
        assert "accounts.google.com" in data["auth_url"]
        assert "client_id" in data
        assert "redirect_uri" in data

    def test_google_sign_up_and_login_flow(self):
        """Verifies Google OAuth auto-registration, RBAC role assignment, and subsequent login."""
        client = TestClient(app)

        # 1. Designated Google Admin User -> ADMIN
        google_token_1 = "mock_google_id_token_shreeya.tcet@gmail.com"
        res_1 = client.post("/api/auth/google", json={"id_token": google_token_1})
        assert res_1.status_code == status.HTTP_200_OK
        data_1 = res_1.json()
        assert data_1["email"] == "shreeya.tcet@gmail.com"
        assert data_1["role"] == "ADMIN"
        assert "access_token" in data_1

        # Verify profile via /api/auth/me
        token_1 = data_1["access_token"]
        me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_1}"})
        assert me_res.status_code == status.HTTP_200_OK
        assert me_res.json()["auth_provider"] == "google"

        # 2. Second Google User -> Auto-assigned DEVELOPER
        google_token_2 = "mock_google_id_token_grace.hopper@navy.mil"
        res_2 = client.post("/api/auth/google", json={"id_token": google_token_2})
        assert res_2.status_code == status.HTTP_200_OK
        data_2 = res_2.json()
        assert data_2["email"] == "grace.hopper@navy.mil"
        assert data_2["role"] == "DEVELOPER"

        # 3. Existing User re-login with Google
        res_login_again = client.post("/api/auth/google", json={"id_token": google_token_1})
        assert res_login_again.status_code == status.HTTP_200_OK
        data_login_again = res_login_again.json()
        assert data_login_again["email"] == "shreeya.tcet@gmail.com"
        assert data_login_again["role"] == "ADMIN"

    def test_google_auth_missing_token_rejection(self):
        """Verifies that requests with no token or code return HTTP 400 Bad Request."""
        client = TestClient(app)
        res = client.post("/api/auth/google", json={})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing Google" in res.json()["detail"]
