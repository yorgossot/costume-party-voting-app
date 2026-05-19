# Party Costume Voting App - "SkpdParto"

> **IMPORTANT**: This file should be kept up-to-date as the codebase evolves. When making significant changes to features, API endpoints, database schema, or configuration, please update this documentation accordingly.

## Production URL
**Live App**: https://skpdparto.up.railway.app/

## Overview
Web app for party guests to upload costume photos, vote for the best costume, and view results. Features a progressive 3-step onboarding wizard, admin controls for competition phases, and a mobile-first single-page application design.

## Tech Stack
- **Backend**: FastAPI + SQLite + JWT authentication (passwordless with access codes)
- **Frontend**: Vanilla HTML/CSS/JavaScript single-page app (served from backend via `frontend/` directory)
- **Deployment**: Railway (single deployment, backend serves both API and frontend)
- **File Storage**: Local filesystem (`backend/data/costumes/`) for costume photos
- **Image Processing**: Pillow with pillow-heif for HEIC/HEIF support, automatic thumbnail generation

## Core Features

### Competition States
The app has 4 distinct states managed by admins:
1. **setup** - Users can onboard, set profiles, upload/change costumes
2. **voting** - Users can vote (up to 5 votes), cannot change profiles/costumes
3. **counting** - Voting closed, results not yet revealed
4. **reveal** - Results visible to all users

### User Flow
1. **Login**: Enter access code (no password required)
2. **Onboarding Wizard** (if first time or incomplete profile):
   - Step 1: Choose display name (4-30 characters)
   - Step 2: Describe costume ("dressed up as" field, 4-30 characters)
   - Step 3: Upload costume photo (camera or gallery)
3. **Main App**: Tab-based interface with 4 sections:
   - **Me**: View/edit your profile and costume
   - **Vote**: Browse all costumes in grid, vote for favorites (max 5)
   - **Results**: Leaderboard (only visible when competition status is "reveal")
   - **Admin**: Control panel (only visible for admin users)

### Photo Handling
- **Formats**: JPEG, PNG, HEIC, HEIF, WebP (max 60 MB)
- **Processing**:
  - Auto-rotation via EXIF data
  - Resize to max 1920px width (85% quality)
  - Automatic thumbnail generation (400px width, 70% quality)
- **Storage**: `backend/data/costumes/` directory
  - Original: `{user_id}_{timestamp}.jpg`
  - Thumbnail: `thumb_{user_id}_{timestamp}.jpg`
- **Serving**: Static files via `/static/costumes/`

### Voting System
- Max 5 votes per user (`MAX_VOTES_PER_USER`)
- Cannot vote for own costume
- Can un-vote to reclaim votes
- Votes stored with unique constraint: one vote per user per person (votes reference `voted_user_id`, not `costume_id`)
- Optional config: `ALLOW_UNREGISTERED_VOTING` (currently `false`, requires complete profile)

### Admin Features
- View current competition status
- Advance status to next phase
- Manually set status to any phase
- **Purge button**: Reset entire app (votes, costumes, profiles) for testing
  - Automatically disabled during party week (Feb 20-27, 2026)
- **User management**: Look up users by access code, reset individual fields (display_name, dressed_up_as, photo), or purge a specific user's data

## Data Models

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    access_code TEXT UNIQUE NOT NULL,
    display_name TEXT,                    -- User's chosen display name
    dressed_up_as TEXT,                   -- Costume description
    is_admin INTEGER NOT NULL DEFAULT 0,  -- Admin flag
    created_at TEXT DEFAULT (datetime('now'))
);
```

### Costumes Table
```sql
CREATE TABLE costumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),  -- One costume per user
    photo_filename TEXT NOT NULL,
    upload_timestamp TEXT DEFAULT (datetime('now'))
);
```

### Votes Table
```sql
CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_id INTEGER NOT NULL REFERENCES users(id),
    voted_user_id INTEGER NOT NULL REFERENCES users(id),
    timestamp TEXT DEFAULT (datetime('now')),
    UNIQUE(voter_id, voted_user_id)  -- Prevents duplicate votes
);
```

### Settings Table
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- Contains: competition_status ('setup', 'voting', 'counting', 'reveal')
```

## API Endpoints

> **REST conventions**: Resource-oriented paths, proper HTTP verbs. `POST`
> creates, `PUT` replaces/sets (idempotent), `PATCH` partially updates,
> `DELETE` removes (idempotent — removing an absent thing still succeeds with
> `204`; `404` only if the *parent* resource is missing). No backward-compat
> aliases — the old RPC-style endpoints were removed.

### Authentication (`/api`)
- `POST /sessions` - Create a session (login with access code, passwordless)
  - Body: `{access_code: string}`
  - Returns `201`: `{token: string, user_id: int, is_admin: bool}`
  - `401` on invalid access code

### User Profile (`/api`)
- `GET /users/me` - Get current user info, costume, and votes
  - Returns: `{user_id, access_code, display_name, dressed_up_as, is_admin, costume: {id, photo_url} | null, votes_used, voted_costume_ids: int[]}`
- `PATCH /users/me` - Partially update profile (authenticated)
  - Body: any subset of `{display_name: string, dressed_up_as: string}` (each 4-30 chars)
  - Only the provided fields are changed; `400` if body is empty
  - Each field can only change during 'setup' phase after first set
  - Returns: `{user_id, ...updated fields}`

### Costumes (`/api`)
- `PUT /users/me/costume` - Upload/replace costume photo (authenticated)
  - Costume is a per-user singleton; PUT replaces any existing one
  - Requires display_name and dressed_up_as to be set first
  - Can only replace costume during 'setup' phase
  - Multipart form-data with image file
  - Returns: `{costume_id: int, filename: string}`
- `GET /costumes` - Get all costumes with metadata
  - Returns: `[{id, user_id, display_name, dressed_up_as, photo_url, thumb_url}]`
  - Vote counts hidden (commented out in code)

### Voting (`/api`)
- `PUT /costumes/{costume_id}/vote` - Cast vote (authenticated, max 5 votes)
  - No body; `costume_id` is in the path. Vote is a sub-resource of a costume
  - Idempotent: voting for an already-voted costume is a no-op success
  - Validates: voting is open, user has profile+costume, not voting for self, under vote limit
  - Returns: `{success: true, votes_remaining: int}`
- `DELETE /costumes/{costume_id}/vote` - Remove vote (authenticated)
  - Idempotent: returns `204` even if the vote did not exist
  - `404` only if the costume itself does not exist
- `GET /results` - Get vote counts and leaderboard
  - Only available when competition_status is 'reveal' (`403` otherwise)
  - Returns top 3 costumes only (LIMIT 3)
  - Returns: `[{costume_id, access_code, display_name, dressed_up_as, photo_url, thumb_url, vote_count}]` (sorted by votes DESC)

### Competition & Admin (`/api`)
- `GET /competition` - Get current competition status (public)
  - Returns: `{status: 'setup' | 'voting' | 'counting' | 'reveal'}`
- `PUT /competition/status` - Set the competition phase (admin only)
  - Body: `{status: string}` (explicit target value; idempotent)
  - To "advance", the client sends the next state in `COMPETITION_STATES`
  - Returns: `{status: string, previous: string}`
- `GET /admin/data` - State of the purgeable data set (admin only)
  - Returns: `{purge_available: bool, votes: int, costumes: int}`
  - `purge_available` is `false` during party week (Feb 20-27, 2026)
- `DELETE /admin/data` - Reset app to clean state (admin only)
  - Deletes all votes, costumes, photo files, resets profiles and status
  - `403` during party week
  - Returns: `{purged: true, votes_deleted: int, costumes_deleted: int, files_deleted: int}`
- `GET /admin/users/{access_code}` - Look up a user by access code (admin only)
  - Returns: `{user_id, display_name, dressed_up_as, has_photo, votes_cast, votes_received}`
  - `404` if no such user
- `DELETE /admin/users/{access_code}/fields/{field}` - Reset one field (admin only)
  - `field` ∈ `display_name | dressed_up_as | photo`; returns `204`
- `DELETE /admin/users/{access_code}/data` - Purge a user's data (admin only)
  - Removes their costume and all votes (cast & received), resets profile; returns `204`

### Protected JavaScript (`/js`)
- `GET /js/admin.js` - Admin panel JavaScript (admin auth required)
- `GET /js/api-auth.js` - API client with auth (requires valid JWT)

## Frontend Architecture

### Single-Page Application
- **File**: `frontend/index.html` (one HTML file with multiple views)
- **Views**: Login, Setup Wizard, Home (Me tab), Vote tab, Results tab, Admin tab
- **Navigation**: Bottom tab bar (visible after login)
- **Modals**: Photo detail, confirmation dialog, field edit dialog
- **Notifications**: Toast system for user feedback

### JavaScript Modules (`frontend/js/`)
- `utils.js` - UI helpers (toast, loading, modals, confirm dialogs)
- `api.js` - API client with JWT auth
- `auth.js` - Login handling, token management
- `setup.js` - 3-step onboarding wizard
- `vote.js` - Costume grid, voting UI, photo modal
- `results.js` - Results/leaderboard view
- `app.js` - Main app controller, tab navigation, routing

### Styling
- `css/styles.css` - Mobile-first responsive design
- Dark theme with purple accents (#1a1a2e background, #6C63FF primary)
- PWA-ready with manifest.json

### Key Features
- **Responsive grid**: Auto-layout costume cards
- **Thumbnail loading**: Fast initial page load with 400px thumbnails
- **Full-size modal**: Click photo to view full resolution
- **Vote feedback**: Heart icons, vote counter badge
- **Character counters**: Real-time feedback on text inputs
- **Progressive enhancement**: Works on older browsers, optimized for mobile

## Configuration (`backend/config.py`)

### Game Settings
- `ALLOW_UNREGISTERED_VOTING = False` - Require profile+costume to vote
- `MAX_VOTES_PER_USER = 5`
- `COMPETITION_STATES = ["setup", "voting", "counting", "reveal"]`

### File Upload
- `MAX_PHOTO_SIZE = 60 * 1024 * 1024` (60 MB)
- `MAX_PHOTO_WIDTH = 1920`
- `THUMB_WIDTH = 400`
- `THUMB_QUALITY = 70`
- `ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"}`

### User Input
- `MIN_FIELD_LENGTH = 4`
- `MAX_FIELD_LENGTH = 30`

### JWT
- `JWT_SECRET` - Environment variable (required in production)
- `JWT_ALGORITHM = "HS256"`
- `JWT_EXPIRY_HOURS = 24`

### Paths
- `DATA_DIR = backend/data/`
- `COSTUMES_DIR = backend/data/costumes/`
- `FRONTEND_DIR = frontend/`

## User Management

### Credential System
- **Access Codes**: Read from `backend/access_codes.txt` (one per line)
- **Admin Codes**: Read from `backend/admin_codes.txt` (one per line)
- **Generation**: Automatic on startup via `generate_credentials.py`
- **No Passwords**: Passwordless authentication (access code only)
- **Script**: `backend/generate_credentials.py` creates users from text files

### Admin Access
- Admin users have `is_admin = 1` in database
- Access code must be in `admin_codes.txt`
- Admin tab visible in UI for admin users
- Can advance/set competition status and purge data

## Deployment

### Railway Production
- **URL**: https://skpdparto.up.railway.app/
- **Environment**: Set `JWT_SECRET` environment variable
- **Build**: Uses `Dockerfile` (Python 3.12-slim)
- **Port**: Dynamic via `${PORT:-8000}`
- **Persistence**: Uses Railway volume for `/app/backend/data/` (costumes + SQLite DB)

### Local Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
fastapi dev main.py
```
- Server runs on http://localhost:8000
- Frontend accessible at root `/`
- API docs at `/docs`

### Database Initialization
- Auto-creates tables on startup via `init_db()`
- Auto-creates users from access code files
- Auto-generates missing thumbnails for existing photos

## Testing Utilities

### `test_utilities/populate.py`
- Script to programmatically create test users, upload costumes, and cast votes
- Useful for seeding data during development

### `test_utilities/locustfile.py`
- Load testing with Locust framework
- Simulates concurrent users voting

## File Structure
```
party_29/
├── backend/
│   ├── data/
│   │   ├── costumes/          # Photo storage
│   │   └── party.db           # SQLite database
│   ├── routers/
│   │   ├── admin.py           # Admin endpoints
│   │   ├── costumes.py        # Photo upload/listing
│   │   ├── protected_js.py    # Auth-protected JS files
│   │   ├── users.py           # Profile management
│   │   └── voting.py          # Vote/unvote/results
│   ├── protected_js/
│   │   ├── admin.js           # Admin UI code
│   │   └── api-auth.js        # Authenticated API client
│   ├── main.py                # FastAPI app entry point
│   ├── config.py              # Configuration constants
│   ├── database.py            # SQLite connection and schema
│   ├── auth.py                # JWT authentication
│   ├── generate_credentials.py
│   ├── access_codes.txt       # User access codes
│   ├── admin_codes.txt        # Admin access codes
│   └── requirements.txt
├── frontend/
│   ├── index.html             # Single-page app
│   ├── css/styles.css
│   ├── js/
│   │   ├── utils.js
│   │   ├── api.js
│   │   ├── auth.js
│   │   ├── setup.js
│   │   ├── vote.js
│   │   ├── results.js
│   │   └── app.js
│   ├── manifest.json          # PWA manifest
│   └── skpdaprto.png         # App icon
├── test_utilities/
│   ├── populate.py
│   └── locustfile.py
├── Dockerfile
└── .gitignore
```

## Success Criteria ✅
- [x] Guests can log in with pre-generated access codes
- [x] Progressive onboarding wizard for new users
- [x] Guests can upload costume photos from phone (camera or gallery)
- [x] Automatic thumbnail generation for fast loading
- [x] HEIC/HEIF format support for iOS users
- [x] Guests can vote for up to 5 costumes (not their own, one vote per costume)
- [x] Un-vote functionality to reclaim votes
- [x] Results page shows live vote counts (when revealed by admin)
- [x] Admin panel to control competition phases
- [x] Mobile-first responsive design
- [x] PWA-ready with manifest
- [x] Successfully deployed to Railway
- [x] Purge button for testing (with safety lockout during party)

## Notes
- **One costume per user**: Enforced by UNIQUE constraint on `costumes.user_id`
- **Profile lock-in**: After setup phase, users cannot change display_name, dressed_up_as, or costume
- **Vote hiding**: Vote counts are hidden from `/api/costumes` endpoint to prevent bias during voting
- **Admin purge safety**: Automatically disabled Feb 20-27, 2026 (party week) to prevent accidental data loss
- **Thumbnail strategy**: Thumbnails (`thumb_*.jpg`) used in grid view, full-size in modal for performance
- **Missing thumbnails**: Auto-generated on startup for any photos without thumbnails
