"""Read usernames from access_codes.txt and admin_codes.txt and insert into the database.

Usage:
    python generate_credentials.py

Reads access codes (one per line) from access_codes.txt (regular users)
and admin_codes.txt (admin users) and creates accounts.
"""

from pathlib import Path
from database import connect_to_db, init_db
from config import COSTUMES_DIR

ACCESS_CODES_FILE = Path(__file__).parent / "access_codes.txt"
ADMIN_CODES_FILE = Path(__file__).parent / "admin_codes.txt"


def _read_codes(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def generate_users_from_access_codes():
    conn = connect_to_db()

    admin_codes = _read_codes(ADMIN_CODES_FILE)
    access_codes = _read_codes(ACCESS_CODES_FILE)
    all_codes = list(admin_codes) + access_codes

    created = []
    for access_code in all_codes:
        try:
            is_admin = 1 if access_code in admin_codes else 0
            conn.execute(
                "INSERT INTO users (access_code, is_admin) VALUES (?, ?)"
                " ON CONFLICT(access_code) DO UPDATE SET is_admin = excluded.is_admin",
                (access_code, is_admin),
            )
            created.append(access_code)
        except Exception:
            # User already exists, skip
            pass

    # Remove users no longer in any list
    placeholders = ",".join("?" * len(all_codes))
    removed_users = conn.execute(
        f"SELECT id, access_code FROM users WHERE access_code NOT IN ({placeholders})",
        all_codes,
    ).fetchall()

    if removed_users:
        removed_ids = [row["id"] for row in removed_users]
        id_placeholders = ",".join("?" * len(removed_ids))

        # Collect photo files to delete
        costume_rows = conn.execute(
            f"SELECT photo_filename FROM costumes WHERE user_id IN ({id_placeholders})",
            removed_ids,
        ).fetchall()

        conn.execute(
            f"DELETE FROM votes WHERE voter_id IN ({id_placeholders}) OR voted_user_id IN ({id_placeholders})",
            removed_ids + removed_ids,
        )
        conn.execute(
            f"DELETE FROM costumes WHERE user_id IN ({id_placeholders})",
            removed_ids,
        )
        conn.execute(
            f"DELETE FROM users WHERE id IN ({id_placeholders})",
            removed_ids,
        )

        for row in costume_rows:
            for filename in (row["photo_filename"], f"thumb_{row['photo_filename']}"):
                path = COSTUMES_DIR / filename
                if path.exists():
                    path.unlink()

    conn.commit()
    conn.close()

    print(f"Created/updated {len(created)} / {len(all_codes)} accounts:")
    for access_code in created:
        label = " (admin)" if access_code in admin_codes else ""
        print(f"  {access_code}{label}")

    if removed_users:
        print(f"Removed {len(removed_users)} unlisted users:")
        for row in removed_users:
            print(f"  {row['access_code']}")
