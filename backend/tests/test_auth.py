"""Tests for authentication (signup/login/me, token handling) and
cross-user data isolation for interviews, dashboard stats, and resumes.

Uses FastAPI's TestClient against an isolated in-memory SQLite database
(dependency override on get_db) so it never touches the real app.db —
schema creation/migration still runs against the real DB on import of
app.main, exactly as it does on normal server startup, but no test data
is ever written there.

Run from backend/: venv/Scripts/python.exe -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all models on Base
from app.core.config import settings
from app.db.base import Base
from app.db.database import get_db
from app.main import app


def _build_minimal_pdf(text: str = "Hello World") -> bytes:
    """Hand-rolled minimal single-page PDF with a real extractable text
    stream, so resume upload's PDF-parsing step succeeds without any
    external dependency (e.g. reportlab)."""
    content = f"BT /F1 24 Tf 100 700 Td ({text}) Tj ET".encode()
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"5 0 obj\n<< /Length %d >>\nstream\n%s\nendstream\nendobj\n"
        % (len(content), content),
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj
    xref_start = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        pdf += b"%010d 00000 n \n" % offset
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        len(objects) + 1,
        xref_start,
    )
    return pdf


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def _signup(self, name="Ada Lovelace", email="ada@example.com", password="supersecret1"):
        return self.client.post(
            "/api/auth/signup",
            json={"name": name, "email": email, "password": password},
        )

    def _login(self, email="ada@example.com", password="supersecret1"):
        return self.client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _signed_up_token(self, email="ada@example.com", password="supersecret1", name="Ada Lovelace"):
        response = self._signup(name=name, email=email, password=password)
        return response.json()["access_token"]


class TestSignup(AuthTestCase):
    def test_signup_success(self):
        response = self._signup()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["token_type"], "bearer")
        self.assertTrue(body["access_token"])
        self.assertEqual(body["user"]["email"], "ada@example.com")
        self.assertEqual(body["user"]["name"], "Ada Lovelace")
        self.assertIn("id", body["user"])
        self.assertIn("created_at", body["user"])

    def test_signup_never_exposes_password_hash(self):
        response = self._signup()
        body = response.json()
        self.assertNotIn("password_hash", body["user"])
        self.assertNotIn("password", body["user"])
        self.assertNotIn("password_hash", str(body))

    def test_duplicate_email_rejected(self):
        first = self._signup(email="dup@example.com")
        self.assertEqual(first.status_code, 201)
        second = self._signup(name="Someone Else", email="dup@example.com")
        self.assertEqual(second.status_code, 400)

    def test_duplicate_email_case_insensitive(self):
        first = self._signup(email="Dup@Example.com")
        self.assertEqual(first.status_code, 201)
        second = self._signup(email="dup@example.com")
        self.assertEqual(second.status_code, 400)

    def test_short_password_rejected(self):
        response = self._signup(password="short")
        self.assertEqual(response.status_code, 422)

    def test_invalid_email_rejected(self):
        response = self._signup(email="not-an-email")
        self.assertEqual(response.status_code, 422)


class TestLogin(AuthTestCase):
    def test_login_success(self):
        self._signup()
        response = self._login()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["access_token"])
        self.assertEqual(body["user"]["email"], "ada@example.com")

    def test_login_invalid_password(self):
        self._signup()
        response = self._login(password="wrong-password")
        self.assertEqual(response.status_code, 401)

    def test_login_unknown_email(self):
        response = self._login(email="ghost@example.com", password="whatever1")
        self.assertEqual(response.status_code, 401)


class TestCurrentUser(AuthTestCase):
    def test_me_without_token(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_me_with_invalid_token(self):
        response = self.client.get(
            "/api/auth/me", headers=self._auth_headers("not-a-real-token")
        )
        self.assertEqual(response.status_code, 401)

    def test_me_with_valid_token(self):
        token = self._signed_up_token()
        response = self.client.get("/api/auth/me", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "ada@example.com")


class TestInterviewIsolation(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.token_a = self._signed_up_token(email="alice@example.com")
        self.token_b = self._signed_up_token(email="bob@example.com", name="Bob")

    def _create_interview(self, token):
        return self.client.post(
            "/api/interviews/",
            json={"role": "Software Engineer", "difficulty": "easy", "question_count": 1},
            headers=self._auth_headers(token),
        )

    def test_create_interview_requires_auth(self):
        response = self.client.post(
            "/api/interviews/",
            json={"role": "Software Engineer", "difficulty": "easy", "question_count": 1},
        )
        self.assertEqual(response.status_code, 401)

    def test_new_interview_belongs_to_authenticated_user(self):
        response = self._create_interview(self.token_a)
        self.assertEqual(response.status_code, 201)

        listing = self.client.get(
            "/api/interviews/", headers=self._auth_headers(self.token_a)
        )
        ids = [i["id"] for i in listing.json()]
        self.assertIn(response.json()["id"], ids)

    def test_user_cannot_list_another_users_interviews(self):
        self._create_interview(self.token_a)
        listing_b = self.client.get(
            "/api/interviews/", headers=self._auth_headers(self.token_b)
        )
        self.assertEqual(listing_b.status_code, 200)
        self.assertEqual(listing_b.json(), [])

    def test_user_cannot_get_another_users_interview(self):
        created = self._create_interview(self.token_a)
        interview_id = created.json()["id"]

        response = self.client.get(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(self.token_b)
        )
        self.assertEqual(response.status_code, 403)

    def test_get_interview_without_token_is_401(self):
        created = self._create_interview(self.token_a)
        interview_id = created.json()["id"]

        response = self.client.get(f"/api/interviews/{interview_id}")
        self.assertEqual(response.status_code, 401)

    def test_get_nonexistent_interview_is_404(self):
        response = self.client.get(
            "/api/interviews/999999", headers=self._auth_headers(self.token_a)
        )
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_complete_another_users_interview(self):
        created = self._create_interview(self.token_a)
        interview_id = created.json()["id"]

        response = self.client.post(
            f"/api/interviews/{interview_id}/complete",
            headers=self._auth_headers(self.token_b),
        )
        self.assertEqual(response.status_code, 403)

    def test_user_cannot_answer_another_users_interview_question(self):
        created = self._create_interview(self.token_a)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        response = self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/answer",
            json={"text": "an answer"},
            headers=self._auth_headers(self.token_b),
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_can_answer_and_complete_their_own_interview(self):
        created = self._create_interview(self.token_a)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        answer_response = self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/answer",
            json={"text": "an answer"},
            headers=self._auth_headers(self.token_a),
        )
        self.assertEqual(answer_response.status_code, 200)

        complete_response = self.client.post(
            f"/api/interviews/{interview_id}/complete",
            headers=self._auth_headers(self.token_a),
        )
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(complete_response.json()["status"], "completed")


class TestDashboardIsolation(AuthTestCase):
    def test_dashboard_requires_auth(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 401)

    def test_dashboard_scoped_to_current_user(self):
        token_a = self._signed_up_token(email="alice@example.com")
        token_b = self._signed_up_token(email="bob@example.com", name="Bob")

        created = self.client.post(
            "/api/interviews/",
            json={"role": "Software Engineer", "difficulty": "easy", "question_count": 1},
            headers=self._auth_headers(token_a),
        )
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]
        self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/answer",
            json={"text": "an answer"},
            headers=self._auth_headers(token_a),
        )
        self.client.post(
            f"/api/interviews/{interview_id}/complete",
            headers=self._auth_headers(token_a),
        )

        dashboard_a = self.client.get(
            "/api/dashboard/", headers=self._auth_headers(token_a)
        )
        self.assertEqual(dashboard_a.json()["overview"]["total_interviews"], 1)

        dashboard_b = self.client.get(
            "/api/dashboard/", headers=self._auth_headers(token_b)
        )
        self.assertEqual(dashboard_b.json()["overview"]["total_interviews"], 0)
        self.assertEqual(dashboard_b.json()["recent_interviews"], [])


class TestResumeIsolation(AuthTestCase):
    def _upload_resume(self, token):
        pdf_bytes = _build_minimal_pdf()
        return self.client.post(
            "/api/resumes/",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
            headers=self._auth_headers(token),
        )

    def test_upload_requires_auth(self):
        pdf_bytes = _build_minimal_pdf()
        response = self.client.post(
            "/api/resumes/",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(response.status_code, 401)

    def test_user_cannot_access_another_users_resume(self):
        token_a = self._signed_up_token(email="alice@example.com")
        token_b = self._signed_up_token(email="bob@example.com", name="Bob")

        uploaded = self._upload_resume(token_a)
        self.assertEqual(uploaded.status_code, 201)
        resume_id = uploaded.json()["id"]

        own_view = self.client.get(
            f"/api/resumes/{resume_id}", headers=self._auth_headers(token_a)
        )
        self.assertEqual(own_view.status_code, 200)

        other_view = self.client.get(
            f"/api/resumes/{resume_id}", headers=self._auth_headers(token_b)
        )
        self.assertEqual(other_view.status_code, 403)

    def test_user_cannot_create_interview_from_another_users_resume(self):
        token_a = self._signed_up_token(email="alice@example.com")
        token_b = self._signed_up_token(email="bob@example.com", name="Bob")

        uploaded = self._upload_resume(token_a)
        resume_id = uploaded.json()["id"]

        response = self.client.post(
            "/api/interviews/",
            json={
                "role": "Software Engineer",
                "difficulty": "easy",
                "question_count": 1,
                "resume_id": resume_id,
            },
            headers=self._auth_headers(token_b),
        )
        self.assertEqual(response.status_code, 400)

    # GET /resumes/ — lets the setup page offer "use a previous resume"
    # instead of requiring a fresh upload every time (see
    # frontend/src/pages/InterviewSetupPage.jsx).
    def test_list_requires_auth(self):
        response = self.client.get("/api/resumes/")
        self.assertEqual(response.status_code, 401)

    def test_list_includes_own_uploads_newest_first(self):
        token = self._signed_up_token()
        first = self._upload_resume(token)
        second = self._upload_resume(token)

        listing = self.client.get("/api/resumes/", headers=self._auth_headers(token))
        self.assertEqual(listing.status_code, 200)
        ids = [r["id"] for r in listing.json()]
        self.assertEqual(ids, [second.json()["id"], first.json()["id"]])

    def test_list_excludes_another_users_resumes(self):
        token_a = self._signed_up_token(email="alice3@example.com")
        token_b = self._signed_up_token(email="bob3@example.com", name="Bob")

        self._upload_resume(token_a)
        self._upload_resume(token_a)
        self._upload_resume(token_b)

        listing_a = self.client.get("/api/resumes/", headers=self._auth_headers(token_a))
        listing_b = self.client.get("/api/resumes/", headers=self._auth_headers(token_b))
        self.assertEqual(len(listing_a.json()), 2)
        self.assertEqual(len(listing_b.json()), 1)

    def test_list_is_empty_for_a_user_with_no_uploads(self):
        token = self._signed_up_token()
        listing = self.client.get("/api/resumes/", headers=self._auth_headers(token))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json(), [])


class TestForgotAndResetPassword(AuthTestCase):
    def test_forgot_password_returns_link_for_registered_email_in_dev_mode(self):
        self._signup(email="reset-me@example.com")
        response = self.client.post(
            "/api/auth/forgot-password", json={"email": "reset-me@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNotNone(body["reset_link"])
        self.assertIn("token=", body["reset_link"])

    def test_forgot_password_does_not_reveal_whether_email_exists(self):
        registered = self.client.post(
            "/api/auth/forgot-password", json={"email": "never-signed-up@example.com"}
        )
        self._signup(email="reset-me2@example.com")
        unregistered = self.client.post(
            "/api/auth/forgot-password", json={"email": "reset-me2@example.com"}
        )
        # Same status code and detail message either way — only reset_link
        # differs, and only because one email has no account to email a
        # link to.
        self.assertEqual(registered.status_code, unregistered.status_code)
        self.assertEqual(registered.json()["detail"], unregistered.json()["detail"])
        self.assertIsNone(registered.json()["reset_link"])

    def test_forgot_password_omits_link_when_dev_mode_disabled(self):
        self._signup(email="prod-like@example.com")
        with patch.object(settings, "password_reset_dev_mode", False):
            response = self.client.post(
                "/api/auth/forgot-password", json={"email": "prod-like@example.com"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["reset_link"])

    def _request_reset_token(self, email: str) -> str:
        response = self.client.post("/api/auth/forgot-password", json={"email": email})
        link = response.json()["reset_link"]
        return link.rsplit("token=", 1)[1]

    def test_reset_password_with_valid_token_allows_new_login(self):
        self._signup(email="reset3@example.com", password="oldpassword1")
        token = self._request_reset_token("reset3@example.com")

        response = self.client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "brandnewpassword1"},
        )
        self.assertEqual(response.status_code, 200)

        old_login = self._login(email="reset3@example.com", password="oldpassword1")
        self.assertEqual(old_login.status_code, 401)
        new_login = self._login(email="reset3@example.com", password="brandnewpassword1")
        self.assertEqual(new_login.status_code, 200)

    def test_reset_token_is_single_use(self):
        self._signup(email="reset4@example.com", password="oldpassword1")
        token = self._request_reset_token("reset4@example.com")

        first = self.client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "firstnewpassword1"},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "secondnewpassword1"},
        )
        self.assertEqual(second.status_code, 400)

    def test_reset_password_rejects_unknown_token(self):
        response = self.client.post(
            "/api/auth/reset-password",
            json={"token": "not-a-real-token", "new_password": "somenewpassword1"},
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_password_rejects_expired_token(self):
        self._signup(email="reset5@example.com", password="oldpassword1")
        with patch.object(settings, "password_reset_expire_minutes", -1):
            token = self._request_reset_token("reset5@example.com")

        response = self.client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "somenewpassword1"},
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_password_rejects_short_password(self):
        self._signup(email="reset6@example.com")
        token = self._request_reset_token("reset6@example.com")
        response = self.client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "short"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
