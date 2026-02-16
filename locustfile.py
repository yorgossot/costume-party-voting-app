"""
Phase-aware load test for the Party Costume Voting App.

Only calls APIs that are valid for the current competition phase:
  - setup:  register (login + profile + upload), browse, re-upload costumes
  - voting: browse, vote (respecting limits), view profile
  - reveal: browse, view results
  - always: browse costumes, view profile, check competition status

Usage:
    pip install locust Pillow

    # With UI (open http://localhost:8089):
    locust -f locustfile.py --host https://YOUR-APP.up.railway.app

    # Headless:
    locust -f locustfile.py --host https://YOUR-APP.up.railway.app \
        --headless -u 50 -r 5 --run-time 2m
"""

import io
import random
import string
import threading
import time
from pathlib import Path

from locust import HttpUser, task, between

# ---------------------------------------------------------------------------
# Access codes — loaded from access_codes.txt, skip first line (admin)
# ---------------------------------------------------------------------------
_ACCESS_CODES_FILE = Path(__file__).parent / "backend" / "access_codes.txt"
ACCESS_CODES = [
    line.strip() for line in _ACCESS_CODES_FILE.read_text().splitlines() if line.strip()
]

MAX_VOTES_PER_USER = 5

# ---------------------------------------------------------------------------
# Fake image — generated once, reused across all users.
# Avoids burning CPU on image generation (we're stress-testing the server).
# ---------------------------------------------------------------------------
_FAKE_IMAGE: bytes | None = None
_IMAGE_LOCK = threading.Lock()


def get_fake_jpeg(width=2400, height=3200):
    """Lazily generate and cache a single fake JPEG (triggers server-side resize)."""
    global _FAKE_IMAGE
    if _FAKE_IMAGE is None:
        with _IMAGE_LOCK:
            if _FAKE_IMAGE is None:
                from PIL import Image

                img = Image.frombytes(
                    "RGB",
                    (width, height),
                    random.randbytes(width * height * 3),
                )
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=85)
                _FAKE_IMAGE = buf.getvalue()
    return _FAKE_IMAGE


# ---------------------------------------------------------------------------
# Unique code assignment — each Locust user gets a distinct access code
# until we run out, then falls back to random reuse.
# ---------------------------------------------------------------------------
_code_counter = 0
_code_lock = threading.Lock()


def _next_code():
    global _code_counter
    with _code_lock:
        idx = _code_counter
        _code_counter += 1
    if idx < len(ACCESS_CODES):
        return ACCESS_CODES[idx]
    return random.choice(ACCESS_CODES)


# ---------------------------------------------------------------------------
# Locust user
# ---------------------------------------------------------------------------
class PartyGuest(HttpUser):
    """Simulates a party guest — phase-aware, only calls valid APIs."""

    wait_time = between(1, 3)

    def on_start(self):
        """Full registration flow: login → sync state → set profile → upload."""
        self.access_code = _next_code()
        self.token = None
        self.user_id = None
        self.phase = "setup"
        self._phase_checked_at = 0.0

        # Local state
        self.has_display_name = False
        self.has_dressed_up_as = False
        self.has_costume = False
        self.my_costume_id = None
        self.costume_ids = []
        self.votes_used = 0
        self.voted_costume_ids = set()

        # --- Login ---
        resp = self.client.post(
            "/api/login",
            json={"access_code": self.access_code},
        )
        if resp.status_code != 200:
            return
        data = resp.json()
        self.token = data["token"]
        self.user_id = data["user_id"]

        # --- Sync existing state from server ---
        self._sync_state()
        self._refresh_phase()

        # --- Set display name (first-time set works in any phase) ---
        if not self.has_display_name:
            name = "Load" + "".join(random.choices(string.ascii_lowercase, k=4))
            resp = self.client.post(
                "/api/select-display-name",
                json={"value": name},
                headers=self._auth(),
            )
            if resp.status_code == 200:
                self.has_display_name = True

        # --- Set costume description (first-time set works in any phase) ---
        if not self.has_dressed_up_as:
            costumes = [
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
            ]
            resp = self.client.post(
                "/api/select-dressed-up-as",
                json={"value": random.choice(costumes)},
                headers=self._auth(),
            )
            if resp.status_code == 200:
                self.has_dressed_up_as = True

        # --- Upload costume (first-time upload works in any phase) ---
        if not self.has_costume:
            resp = self.client.post(
                "/api/upload-costume",
                files={"file": ("costume.jpg", get_fake_jpeg(), "image/jpeg")},
                headers=self._auth(),
            )
            if resp.status_code == 200:
                self.has_costume = True
                self.my_costume_id = resp.json().get("costume_id")

    # -- Helpers ----------------------------------------------------------

    def _auth(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _refresh_phase(self):
        """Fetch competition status, cached for 5 seconds."""
        now = time.time()
        if now - self._phase_checked_at < 5:
            return
        self._phase_checked_at = now
        resp = self.client.get(
            "/api/competition-status",
            name="/api/competition-status",
        )
        if resp.status_code == 200:
            self.phase = resp.json().get("status", self.phase)

    def _sync_state(self):
        """Pull current user state from /api/me."""
        resp = self.client.get("/api/me", headers=self._auth(), name="/api/me [sync]")
        if resp.status_code != 200:
            return
        data = resp.json()
        self.has_display_name = bool(data.get("display_name"))
        self.has_dressed_up_as = bool(data.get("dressed_up_as"))
        costume = data.get("costume")
        if costume:
            self.has_costume = True
            self.my_costume_id = costume["id"]
        self.votes_used = data.get("votes_used", 0)
        self.voted_costume_ids = set(data.get("voted_costume_ids", []))

    # -- Tasks ------------------------------------------------------------

    @task(3)
    def browse_costumes(self):
        """Browse the costume gallery — always valid."""
        if not self.token:
            return
        resp = self.client.get("/api/costumes")
        if resp.status_code == 200:
            costumes = resp.json()
            self.costume_ids = [c["id"] for c in costumes]

    @task(3)
    def vote_for_costume(self):
        """Vote for a random costume — only during voting phase.
        If all votes are used, unvote one first to free a slot."""
        if not self.token:
            return
        self._refresh_phase()
        if self.phase != "voting":
            return
        if not self.costume_ids:
            return

        # If maxed out, unvote a random one first to free a slot
        if self.votes_used >= MAX_VOTES_PER_USER and self.voted_costume_ids:
            drop = random.choice(list(self.voted_costume_ids))
            resp = self.client.post(
                "/api/unvote",
                json={"costume_id": drop},
                headers=self._auth(),
            )
            if resp.status_code == 200:
                self.votes_used -= 1
                self.voted_costume_ids.discard(drop)
            else:
                return

        candidates = [
            cid
            for cid in self.costume_ids
            if cid != self.my_costume_id and cid not in self.voted_costume_ids
        ]
        if not candidates:
            return

        target = random.choice(candidates)
        resp = self.client.post(
            "/api/vote",
            json={"costume_id": target},
            headers=self._auth(),
        )
        if resp.status_code == 200:
            self.votes_used += 1
            self.voted_costume_ids.add(target)

    @task(1)
    def unvote_costume(self):
        """Unvote a previously voted costume — only during voting phase."""
        if not self.token:
            return
        self._refresh_phase()
        if self.phase != "voting":
            return
        if not self.voted_costume_ids:
            return

        target = random.choice(list(self.voted_costume_ids))
        resp = self.client.post(
            "/api/unvote",
            json={"costume_id": target},
            headers=self._auth(),
        )
        if resp.status_code == 200:
            self.votes_used -= 1
            self.voted_costume_ids.discard(target)

    @task(1)
    def reupload_costume(self):
        """Re-upload costume photo — only during setup phase."""
        if not self.token or not self.has_costume:
            return
        self._refresh_phase()
        if self.phase != "setup":
            return
        self.client.post(
            "/api/upload-costume",
            files={"file": ("costume.jpg", get_fake_jpeg(), "image/jpeg")},
            headers=self._auth(),
        )

    @task(1)
    def check_results(self):
        """Check the leaderboard — only during reveal phase."""
        if not self.token:
            return
        self._refresh_phase()
        if self.phase != "reveal":
            return
        self.client.get("/api/results", headers=self._auth())

    @task(2)
    def view_profile(self):
        """Check own profile — always valid."""
        if not self.token:
            return
        self.client.get("/api/me", headers=self._auth())

    @task(1)
    def refresh_phase(self):
        """Explicitly check competition status — always valid."""
        if not self.token:
            return
        self._refresh_phase()
