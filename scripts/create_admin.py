"""One-off: create or promote an admin user in staff_admins."""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.auth import hash_password
from app.database import get_connection


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or promote an admin account")
    parser.add_argument("--email", default="admin@imprint.local")
    parser.add_argument(
        "--password",
        default=None,
        help="Omit to auto-generate a random password (printed once on success).",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Update password for an existing user (requires --password).",
    )
    parser.add_argument("--name", default="系統管理員")
    parser.add_argument("--phone", default="0900000000")
    args = parser.parse_args()

    email = args.email.strip().lower()
    password = args.password or secrets.token_urlsafe(12)
    if len(password) < 6:
        print("Password must be at least 6 characters", file=sys.stderr)
        return 1
    if args.reset_password and not args.password:
        print("--reset-password requires --password", file=sys.stderr)
        return 1

    created = False
    reset = False
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email from users where email = %s", (email,))
        user = cur.fetchone()

        if user:
            user_id = str(user["id"])
            cur.execute(
                "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                (user_id,),
            )
            if args.reset_password or args.password:
                cur.execute(
                    "update users set password_hash = %s where id = %s",
                    (hash_password(password), user_id),
                )
                reset = True
                print(f"Promoted + reset password: {email}")
            else:
                print(f"Promoted existing user to admin: {email}")
                print("(Password unchanged. Pass --password to reset it.)")
        else:
            created = True
            password_hash = hash_password(password)
            cur.execute(
                """
                insert into users (email, password_hash, email_verified)
                values (%s, %s, true)
                returning id, email
                """,
                (email, password_hash),
            )
            user = cur.fetchone()
            user_id = str(user["id"])
            cur.execute(
                "insert into profiles (id, full_name, phone) values (%s, %s, %s)",
                (user_id, args.name, args.phone),
            )
            cur.execute(
                "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                (user_id,),
            )
            print(f"Created admin account: {email}")

    print("Login at /login.html then open /admin.html")
    if created or reset:
        print(f"Password: {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
