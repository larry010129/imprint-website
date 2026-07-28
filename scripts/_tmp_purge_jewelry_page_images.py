from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.content import ensure_page_images_schema
from app.database import get_connection
from app.seed_content import seed_content_if_empty

with get_connection() as conn, conn.cursor() as cur:
    ensure_page_images_schema(cur)
    cur.execute(
        "select count(*) as c from page_images "
        "where page_key like %s or page_key like %s or page_key = %s or group_key = %s",
        ("/shop/%", "/jewelry/%", "/jewelry/", "jewelry"),
    )
    print("leftover shop/jewelry after schema purge:", cur.fetchone())
    cur.execute("select count(*) as c from page_images")
    print("total page_images:", cur.fetchone())

print("seed created:", seed_content_if_empty())

with get_connection() as conn, conn.cursor() as cur:
    cur.execute("select distinct page_key from page_images order by 1")
    for row in cur.fetchall():
        print(" ", row["page_key"])
