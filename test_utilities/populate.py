"""
Populate the backend with all users from access_codes.txt.

For each user: login, set display name, set costume description, upload a fake photo.

Usage:
    python test_utilities/populate.py [--host HOST]

    --host  Base URL of the backend (default: http://localhost:8000)
"""

import argparse
import io
import random
import string
import sys
from pathlib import Path

import requests
from PIL import Image

ACCESS_CODES_FILE = Path(__file__).parent.parent / "backend" / "access_codes.txt"

COSTUMES = [
    "Vampire",
    "Ghost",
    "Pirate",
    "Witch",
    "Zombie",
    "Robot",
    "Alien",
    "Ninja",
    "Dragon",
    "Wizard",
    "Mummy",
    "Skeleton",
    "Werewolf",
    "Fairy",
    "Knight",
]

DISPLAY_NAMES = [
    "Alex",
    "Blake",
    "Casey",
    "Drew",
    "Ellis",
    "Frankie",
    "Gray",
    "Harper",
    "Indie",
    "Jules",
    "Kit",
    "Lane",
    "Morgan",
    "Noel",
    "Oakley",
    "Parker",
    "Quinn",
    "Reese",
    "Sage",
    "Tatum",
]


def make_fake_jpeg(width=800, height=1000) -> bytes:
    """Generate a small random JPEG image."""
    img = Image.frombytes("RGB", (width, height), random.randbytes(width * height * 3))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return buf.getvalue()


def populate(host: str):
    codes = [
        line.strip()
        for line in ACCESS_CODES_FILE.read_text().splitlines()
        if line.strip()
    ]
    if not codes:
        print("No access codes found in", ACCESS_CODES_FILE)
        sys.exit(1)

    print(f"Populating {len(codes)} users on {host}\n")

    fake_image = make_fake_jpeg()
    success = 0
    errors = 0

    for i, code in enumerate(codes, 1):
        label = f"[{i}/{len(codes)}] {code}"

        # Login
        resp = requests.post(f"{host}/api/login", json={"access_code": code})
        if resp.status_code != 200:
            print(f"  {label} - LOGIN FAILED ({resp.status_code})")
            errors += 1
            continue
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Set display name
        name = random.choice(DISPLAY_NAMES) + "".join(
            random.choices(string.digits, k=2)
        )
        resp = requests.post(
            f"{host}/api/select-display-name",
            json={"value": name},
            headers=headers,
        )
        name_ok = resp.status_code == 200

        # Set costume description
        costume_desc = random.choice(COSTUMES)
        resp = requests.post(
            f"{host}/api/select-dressed-up-as",
            json={"value": costume_desc},
            headers=headers,
        )
        desc_ok = resp.status_code == 200

        # Upload costume photo
        resp = requests.post(
            f"{host}/api/upload-costume",
            files={"file": ("costume.jpg", fake_image, "image/jpeg")},
            headers=headers,
        )
        photo_ok = resp.status_code == 200

        status = "OK" if (name_ok and desc_ok and photo_ok) else "PARTIAL"
        details = []
        if not name_ok:
            details.append("name failed")
        if not desc_ok:
            details.append("desc failed")
        if not photo_ok:
            details.append("photo failed")

        extra = f" ({', '.join(details)})" if details else ""
        print(f"  {label} - {status}{extra}")

        if name_ok and desc_ok and photo_ok:
            success += 1
        else:
            errors += 1

    print(f"\nDone: {success} ok, {errors} errors out of {len(codes)} users")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate backend with test users")
    parser.add_argument(
        "--host", default="http://localhost:8000", help="Backend base URL"
    )
    args = parser.parse_args()
    populate(args.host)
