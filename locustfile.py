"""
Load test for the Party Costume Voting App.

Usage:
    # Install locust (+ Pillow for fake image generation)
    pip install locust Pillow

    # Run against your Railway deployment
    locust -f locustfile.py --host https://YOUR-APP.up.railway.app

    # Then open http://localhost:8089 in your browser to configure and start the test.
    #
    # Or run headless (no UI):
    locust -f locustfile.py --host https://YOUR-APP.up.railway.app \
        --headless -u 50 -r 5 --run-time 2m
    #   -u 50     = 50 concurrent users
    #   -r 5      = spawn 5 users per second
    #   --run-time = stop after 2 minutes
"""

import random
import string
import io
from locust import HttpUser, task, between


# Access codes from access_codes.txt (excluding admin)
ACCESS_CODES = [
    "turbulent-platypus",
    "melodramatic-shrimp",
    "suspicious-flamingo",
    "bewildered-walrus",
    "flamboyant-iguana",
    "hysterical-pelican",
    "paranoid-chinchilla",
    "volcanic-hamster",
    "existential-penguin",
    "ludicrous-moose",
    "radioactive-sloth",
    "pretentious-wombat",
    "chaotic-narwhal",
    "philosophical-crab",
    "unhinged-alpaca",
    "flirtatious-hippo",
    "caffeinated-gecko",
    "delusional-otter",
    "spectacular-ferret",
    "neurotic-toucan",
    "magnificent-squid",
    "dramatic-capybara",
    "reckless-puffin",
    "mystical-badger",
    "ridiculous-yak",
    "explosive-seahorse",
    "sarcastic-koala",
    "legendary-axolotl",
    "turbocharged-snail",
    "diabolical-quokka",
    "outrageous-lobster",
    "psychedelic-mole",
    "overthinking-swan",
    "glamorous-warthog",
    "thunderous-lemur",
    "eccentric-mantis",
    "furious-duckling",
    "hallucinating-seal",
    "intergalactic-newt",
    "bonkers-pangolin",
    "flammable-parrot",
    "colossal-chipmunk",
    "melodious-scorpion",
    "irrational-ostrich",
    "fabulous-armadillo",
    "supersonic-tortoise",
    "haunted-macaw",
    "ominous-bunny",
    "rebellious-starfish",
]


def make_fake_jpeg(width=3024, height=4032):
    """Generate a realistic phone-photo-sized JPEG with random noise (hard to compress)."""
    from PIL import Image

    # Random pixel noise — incompressible, simulates real photo complexity
    img = Image.frombytes(
        "RGB",
        (width, height),
        random.randbytes(width * height * 3),
    )
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf.read()


class PartyGuest(HttpUser):
    """Simulates a party guest using the costume voting app."""

    # Wait 1-3 seconds between actions (realistic browsing)
    wait_time = between(1, 3)

    def on_start(self):
        """Full guest setup: login → display name → costume description → upload photo."""
        self.access_code = random.choice(ACCESS_CODES)
        self.token = None
        self.user_id = None
        self.costume_ids = []
        self.my_costume_id = None

        # Login
        resp = self.client.post(
            "/api/login",
            json={
                "access_code": self.access_code,
            },
        )
        if resp.status_code != 200:
            return
        data = resp.json()
        self.token = data["token"]
        self.user_id = data["user_id"]

        # Set display name (random 6-char name)
        display_name = "Load" + "".join(random.choices(string.ascii_lowercase, k=4))
        self.client.post(
            "/api/select-display-name",
            json={"value": display_name},
            headers=self.auth_headers(),
        )

        # Set costume description
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
        self.client.post(
            "/api/select-dressed-up-as",
            json={"value": random.choice(costumes)},
            headers=self.auth_headers(),
        )

        # Upload costume photo
        self.client.post(
            "/api/upload-costume",
            files={"file": ("costume.jpg", make_fake_jpeg(), "image/jpeg")},
            headers=self.auth_headers(),
        )

    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def browse_costumes(self):
        """Most common action: browsing the costume gallery."""
        resp = self.client.get("/api/costumes")
        if resp.status_code == 200:
            costumes = resp.json()
            self.costume_ids = [c["id"] for c in costumes]
            for c in costumes:
                if c.get("user_id") == self.user_id:
                    self.my_costume_id = c["id"]

    @task(2)
    def view_own_profile(self):
        """Check own profile / status."""
        self.client.get("/api/me", headers=self.auth_headers())

    @task(2)
    def vote_for_costume(self):
        """Vote for a random costume (not own)."""
        if not self.costume_ids:
            return
        candidates = [cid for cid in self.costume_ids if cid != self.my_costume_id]
        if not candidates:
            return
        self.client.post(
            "/api/vote",
            json={"costume_id": random.choice(candidates)},
            headers=self.auth_headers(),
        )

    @task(1)
    def upload_costume(self):
        """Upload a costume photo."""
        self.client.post(
            "/api/upload-costume",
            files={"file": ("costume.jpg", make_fake_jpeg(), "image/jpeg")},
            headers=self.auth_headers(),
        )

    @task(1)
    def check_results(self):
        """Check the results/leaderboard."""
        self.client.get("/api/results", headers=self.auth_headers())

    @task(1)
    def check_competition_status(self):
        """Check current competition phase."""
        self.client.get("/api/competition-status")

    @task(1)
    def load_frontend_page(self):
        """Simulate loading frontend static pages."""
        page = random.choice(["/", "/vote.html", "/results.html", "/upload.html"])
        self.client.get(page, name="/[frontend page]")
