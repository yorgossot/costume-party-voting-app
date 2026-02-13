"""Read usernames from usernames.txt and insert into the database.

Usage:
    python generate_credentials.py

Reads access_codes (one per line) from access_codes.txt and creates accounts.
The first access_code in the file is created as an admin.
"""

from pathlib import Path
from database import connect_to_db, init_db

ACCESS_CODES_FILE = Path(__file__).parent / "access_codes.txt"


def generate_users_from_access_codes():
    conn = connect_to_db()

    access_codes = [
        line.strip()
        for line in ACCESS_CODES_FILE.read_text().splitlines()
        if line.strip()
    ]

    admin_access_code = access_codes[0] if access_codes else None

    created = []
    for access_code in access_codes:
        try:
            is_admin = 1 if access_code == admin_access_code else 0
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

    print(f"Created {len(created)} / {len(access_codes)} accounts:")
    for access_code in created:
        label = " (admin)" if access_code == admin_access_code else ""
        print(f"  {access_code}{label}")
