"""Read usernames from access_codes.txt and admin_codes.txt and insert into the database.

Usage:
    python generate_credentials.py

Reads access codes (one per line) from access_codes.txt (regular users)
and admin_codes.txt (admin users) and creates accounts.
"""

from pathlib import Path
from database import connect_to_db, init_db

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
                "INSERT INTO users (access_code, is_admin) VALUES (?, ?)",
                (access_code, is_admin),
            )
            created.append(access_code)
        except Exception:
            # User already exists, skip
            pass

    conn.commit()
    conn.close()

    print(f"Created {len(created)} / {len(all_codes)} accounts:")
    for access_code in created:
        label = " (admin)" if access_code in admin_codes else ""
        print(f"  {access_code}{label}")
