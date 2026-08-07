"""TOTP 2FA — unit tests and API/HTMX integration (requires DATABASE_URL)."""



from __future__ import annotations



import os

import uuid

from datetime import datetime, timedelta, timezone

from pathlib import Path



import jwt

import pyotp

import pytest

from dotenv import load_dotenv



load_dotenv(Path(__file__).resolve().parents[1] / ".env")

os.environ.setdefault("STARTUP_SEED_MODE", "off")

os.environ.setdefault("JWT_SECRET", os.environ.get("JWT_SECRET", "test-jwt-secret-for-totp"))



from app.auth import (

    PRE2FA_COOKIE_NAME,

    PRE2FA_MINUTES,

    PWRESET_COOKIE_NAME,

    PWRESET_MINUTES,

    COOKIE_NAME,

    hash_password,

    sign_pre2fa,

    sign_pwreset,

    verify_pre2fa,

    verify_pwreset,

    verify_session_token,

)

from app.auth_totp_service import PWRESET_GENERIC_ERR

from app.totp import (

    burn_backup_code,

    generate_backup_codes,

    generate_secret,

    hash_backup_codes,

    verify_backup_code,

    verify_totp,

)





@pytest.fixture(scope="module")

def client():

    from fastapi.testclient import TestClient



    from app import create_app



    with TestClient(create_app()) as c:

        yield c





def test_verify_totp_accepts_valid_window():

    secret = generate_secret()

    code = pyotp.TOTP(secret).now()

    assert verify_totp(secret, code, valid_window=1)





def test_verify_totp_rejects_invalid_code():

    secret = generate_secret()

    assert not verify_totp(secret, "000000", valid_window=1)





def test_backup_code_burn_once():

    plain = generate_backup_codes(2)

    hashed = hash_backup_codes(plain)

    idx = verify_backup_code(plain[0], hashed)

    assert idx == 0

    remaining = burn_backup_code(hashed, idx)

    assert len(remaining) == 1

    assert verify_backup_code(plain[0], remaining) is None

    assert verify_backup_code(plain[1], remaining) == 0





def test_pre2fa_token_expires():

    token = sign_pre2fa(str(uuid.uuid4()))

    assert verify_pre2fa(token)



    secret = os.environ["JWT_SECRET"]

    payload = jwt.decode(token, secret, algorithms=["HS256"])

    payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)

    expired = jwt.encode(payload, secret, algorithm="HS256")

    assert verify_pre2fa(expired) is None





def test_pre2fa_not_accepted_as_session():

    token = sign_pre2fa(str(uuid.uuid4()))

    assert verify_session_token(token) is None





def test_pre2fa_ttl_is_five_minutes():

    assert PRE2FA_MINUTES == 5


def test_pwreset_token_roundtrip():

    token = sign_pwreset(str(uuid.uuid4()))

    assert verify_pwreset(token)


def test_pwreset_not_accepted_as_session():

    token = sign_pwreset(str(uuid.uuid4()))

    assert verify_session_token(token) is None


def test_pwreset_ttl_is_ten_minutes():

    assert PWRESET_MINUTES == 10





@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="DATABASE_URL not set")

class TestTotpIntegration:

    @pytest.fixture(autouse=True)

    def _ensure_columns(self):

        from app.totp import ensure_totp_columns

        from app.database import get_connection



        ensure_totp_columns()

        with get_connection() as conn, conn.cursor() as cur:

            cur.execute("delete from login_lockouts where lockout_key like 'pwreset-totp:%'")



    def _create_user(self, *, admin: bool = False, totp_enabled: bool = False) -> tuple[str, str, str]:

        from app.database import get_connection



        email = f"totp-test-{uuid.uuid4().hex[:10]}@example.com"

        password = "password123"

        secret = generate_secret()

        with get_connection() as conn, conn.cursor() as cur:

            cur.execute(

                """

                insert into users (email, password_hash, email_verified, totp_secret, totp_enabled)

                values (%s, %s, true, %s, %s)

                returning id

                """,

                (email, hash_password(password), secret if totp_enabled else None, totp_enabled),

            )

            user_id = str(cur.fetchone()["id"])

            if admin:

                cur.execute(

                    "insert into staff_admins (user_id) values (%s) on conflict do nothing",

                    (user_id,),

                )

        return user_id, email, password



    def _cleanup(self, user_id: str) -> None:

        from app.database import get_connection



        with get_connection() as conn, conn.cursor() as cur:

            cur.execute("delete from staff_admins where user_id = %s", (user_id,))

            cur.execute("delete from users where id = %s", (user_id,))



    def test_login_issues_full_session_with_totp(self, client):

        user_id, email, password = self._create_user(totp_enabled=True)

        try:

            resp = client.post(

                "/api/auth/login",

                json={"email": email, "password": password},

            )

            assert resp.status_code == 200

            data = resp.json()

            assert data.get("requires2fa") is not True

            assert COOKIE_NAME in resp.cookies

            assert PRE2FA_COOKIE_NAME not in resp.cookies or not resp.cookies.get(PRE2FA_COOKIE_NAME)

        finally:

            self._cleanup(user_id)



    def test_admin_with_totp_requires_pre2fa(self, client):

        from app.database import get_connection

        user_id, email, password = self._create_user(admin=True, totp_enabled=True)

        try:

            with get_connection() as conn, conn.cursor() as cur:

                cur.execute("select totp_secret from users where id = %s", (user_id,))

                secret = cur.fetchone()["totp_secret"]

            login = client.post(

                "/api/auth/login",

                json={"email": email, "password": password},

            )

            assert login.status_code == 200

            data = login.json()

            assert data.get("requires2fa") is True

            assert "/login-2fa" in (data.get("next") or "")

            assert COOKIE_NAME not in login.cookies or not login.cookies.get(COOKIE_NAME)

            assert PRE2FA_COOKIE_NAME in login.cookies



            code = pyotp.TOTP(secret).now()

            verify = client.post(

                "/api/auth/verify-2fa",

                json={"code": code, "next": "/account"},

                cookies=login.cookies,

            )

            assert verify.status_code == 200

            assert COOKIE_NAME in verify.cookies

            admin_api = client.get("/api/admin/orders", cookies=verify.cookies)

            assert admin_api.status_code != 403

        finally:

            self._cleanup(user_id)



    def test_htmx_login_redirects_to_next_not_2fa(self, client):

        user_id, email, password = self._create_user(totp_enabled=True)

        try:

            resp = client.post(

                "/htmx/auth/login",

                headers={"HX-Request": "true"},

                data={"email": email, "password": password, "next": "/account"},

            )

            assert resp.status_code == 200

            assert "/login-2fa" not in resp.headers.get("HX-Redirect", "")

            assert "/account" in resp.headers.get("HX-Redirect", "")

            assert COOKIE_NAME in resp.cookies

        finally:

            self._cleanup(user_id)



    def test_reset_password_with_valid_totp(self, client):

        user_id, email, _old_password = self._create_user(totp_enabled=True)

        new_password = "newpass456"

        try:

            from app.database import get_connection



            with get_connection() as conn, conn.cursor() as cur:

                cur.execute("select totp_secret from users where id = %s", (user_id,))

                secret = cur.fetchone()["totp_secret"]

            code = pyotp.TOTP(secret).now()



            verify = client.post(

                "/api/auth/forgot-password-verify",

                json={"email": email, "code": code},

            )

            assert verify.status_code == 200

            assert PWRESET_COOKIE_NAME in verify.cookies



            resp = client.post(

                "/api/auth/reset-password-totp",

                json={"newPassword": new_password},

                cookies=verify.cookies,

            )

            assert resp.status_code == 200

            assert resp.json().get("ok") is True



            login = client.post(

                "/api/auth/login",

                json={"email": email, "password": new_password},

            )

            assert login.status_code == 200

        finally:

            self._cleanup(user_id)



    def test_htmx_forgot_password_two_step_flow(self, client):

        user_id, email, _old_password = self._create_user(totp_enabled=True)

        new_password = "newpass456"

        try:

            from app.database import get_connection



            with get_connection() as conn, conn.cursor() as cur:

                cur.execute("select totp_secret from users where id = %s", (user_id,))

                secret = cur.fetchone()["totp_secret"]

            code = pyotp.TOTP(secret).now()



            verify = client.post(

                "/htmx/auth/forgot-password-verify",

                headers={"HX-Request": "true"},

                data={"email": email, "code": code},

            )

            assert verify.status_code == 200

            assert PWRESET_COOKIE_NAME in verify.cookies

            assert "驗證成功" in verify.text



            complete = client.post(

                "/htmx/auth/forgot-password",

                headers={"HX-Request": "true"},

                cookies=verify.cookies,

                data={"password": new_password, "passwordConfirm": new_password},

                follow_redirects=False,

            )

            assert complete.status_code == 200

            assert complete.headers.get("HX-Redirect") == "/login"

            assert PWRESET_COOKIE_NAME not in complete.cookies or complete.cookies.get(PWRESET_COOKIE_NAME) == ""



            login = client.post(

                "/api/auth/login",

                json={"email": email, "password": new_password},

            )

            assert login.status_code == 200

        finally:

            self._cleanup(user_id)



    def test_reset_password_without_pwreset_cookie_fails(self, client):

        user_id, email, _password = self._create_user(totp_enabled=True)

        try:

            resp = client.post(

                "/api/auth/reset-password-totp",

                json={"newPassword": "newpass456"},

            )

            assert resp.status_code == 401

            assert resp.json().get("error")

        finally:

            self._cleanup(user_id)



    def test_reset_password_wrong_code_fails(self, client):

        user_id, email, _password = self._create_user(totp_enabled=True)

        try:

            resp = client.post(

                "/api/auth/forgot-password-verify",

                json={"email": email, "code": "000000"},

            )

            assert resp.status_code == 401

            assert resp.json().get("error") == PWRESET_GENERIC_ERR

        finally:

            self._cleanup(user_id)



    def test_reset_password_no_totp_enrolled_fails(self, client):

        user_id, email, _password = self._create_user(totp_enabled=False)

        try:

            resp = client.post(

                "/api/auth/forgot-password-verify",

                json={"email": email, "code": "123456"},

            )

            assert resp.status_code == 401

            assert resp.json().get("error") == PWRESET_GENERIC_ERR

        finally:

            self._cleanup(user_id)



    def test_disable_totp_blocks_forgot_password_reset(self, client):

        user_id, email, password = self._create_user(totp_enabled=True)

        try:

            with get_connection() as conn, conn.cursor() as cur:

                cur.execute("select totp_secret from users where id = %s", (user_id,))

                secret = cur.fetchone()["totp_secret"]

            code = pyotp.TOTP(secret).now()



            login = client.post(

                "/api/auth/login",

                json={"email": email, "password": password},

            )

            assert login.status_code == 200



            disable = client.post(

                "/api/auth/totp/disable",

                json={"password": password, "code": code},

                cookies=login.cookies,

            )

            assert disable.status_code == 200

            assert disable.json().get("ok") is True



            resp = client.post(

                "/api/auth/forgot-password-verify",

                json={"email": email, "code": code},

            )

            assert resp.status_code == 401

            assert resp.json().get("error") == PWRESET_GENERIC_ERR

        finally:

            self._cleanup(user_id)



    def test_admin_can_disable_totp(self, client):

        user_id, email, password = self._create_user(admin=True, totp_enabled=True)

        try:

            with get_connection() as conn, conn.cursor() as cur:

                cur.execute("select totp_secret from users where id = %s", (user_id,))

                secret = cur.fetchone()["totp_secret"]

            code = pyotp.TOTP(secret).now()

            login = client.post(

                "/api/auth/login",

                json={"email": email, "password": password},

            )

            assert login.status_code == 200

            assert login.json().get("requires2fa") is True

            verify = client.post(

                "/api/auth/verify-2fa",

                json={"code": code},

                cookies=login.cookies,

            )

            assert verify.status_code == 200

            # Fresh code after verify consumed the previous window (usually still valid).
            code2 = pyotp.TOTP(secret).now()

            disable = client.post(

                "/api/auth/totp/disable",

                json={"password": password, "code": code2},

                cookies=verify.cookies,

            )

            assert disable.status_code == 200

        finally:

            self._cleanup(user_id)



    def test_totp_setup_start_and_confirm(self, client):

        user_id, email, password = self._create_user(totp_enabled=False)

        try:

            login = client.post(

                "/api/auth/login",

                json={"email": email, "password": password},

            )

            assert login.status_code == 200

            cookies = login.cookies



            start = client.post("/api/auth/totp/setup/start", cookies=cookies)

            assert start.status_code == 200

            data = start.json()

            assert data.get("ok") is True

            assert data.get("secret")

            assert str(data.get("qrDataUrl", "")).startswith("data:image")



            code = pyotp.TOTP(data["secret"]).now()

            confirm = client.post(

                "/api/auth/totp/setup/confirm",

                json={"code": code},

                cookies=cookies,

            )

            assert confirm.status_code == 200

            confirm_data = confirm.json()

            assert confirm_data.get("ok") is True

            assert len(confirm_data.get("backupCodes", [])) > 0



            partial = client.get(

                "/htmx/account-security",

                cookies=cookies,

                headers={"HX-Request": "true"},

            )

            assert partial.status_code == 200

            assert 'id="totp-start-btn"' not in partial.text

            assert "已啟用 Authenticator" in partial.text

        finally:

            self._cleanup(user_id)





# late import for integration helper

from app.database import get_connection  # noqa: E402

