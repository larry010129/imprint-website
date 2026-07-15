"""One-off: create or promote an admin user in staff_admins."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.auth import hash_password
from app.database import get_connection


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or promote an admin account")
    parser.add_argument("--email", default="admin@imprint.local")
    parser.add_argument("--password", default="Admin123!")
    parser.add_argument("--name", default="系統管理員")
    parser.add_argument("--phone", default="0900000000")
    args = parser.parse_args()

    email = args.email.strip().lower()
    if len(args.password) < 6:
        print("Password must be at least 6 characters", file=sys.stderr)
        return 1

    created = False
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select id, email from users where email = %s", (email,))
        user = cur.fetchone()

        if user:
            user_id = str(user["id"])
            cur.execute(
                "insert into staff_admins (user_id) values (%s) on conflict do nothing",
                (user_id,),
            )
            print(f"Promoted existing user to admin: {email}")
        else:
            created = True
            password_hash = hash_password(args.password)
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
    if created:
        print(f"Password: {args.password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
