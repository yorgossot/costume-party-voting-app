# Party Costume Voting App

## Overview
Web app for party guests to upload costume photos, vote for best costume, and optionally complete tasks. Pre-generated credentials for authentication.

## Tech Stack
- **Backend**: FastAPI + SQLite + JWT authentication
- **Frontend**: Vanilla HTML/CSS/JavaScript (served from backend via `frontend/` directory)
- **Deployment**: Single deployment on Railway/Render (backend serves both API and frontend)
- **File Storage**: Local filesystem on backend server for costume photos (**TBD**: may need persistent volume or S3 depending on deployment platform — ephemeral storage risks losing uploads on restart)

## Core Features (Priority Order)
1. User authentication with pre-generated credentials
2. Costume photo upload (phone camera/file upload)
3. Voting system (up to 5 votes per user, cannot vote for own costume)
4. Hidden results/leaderboard (revealed when voting closes)
5. *Optional*: Task system for party challenges

## Data Models

### Users
- id (primary key)
- access_code (unique)
- password_hash
- created_at

### Costumes
- id (primary key)
- user_id (foreign key, **unique** — one costume per user)
- photo_filename
- upload_timestamp

### Votes
- id (primary key)
- voter_id (foreign key to Users)
- costume_id (foreign key to Costumes)
- timestamp
- **Constraint**: Max `MAX_VOTES_PER_USER` votes per voter_id (unique on voter_id + costume_id pair, check count before inserting)

### Tasks (Optional)
- id (primary key)
- user_id (foreign key)
- description
- completed (boolean)
- evidence_photo (nullable)
- completed_at (nullable)

## API Endpoints

### Authentication
- `POST /api/login` - Login with credentials, returns JWT token
  - Body: `{access_code, password}`
  - Returns: `{token, user_id}`

### Costumes
- `POST /api/upload-costume` - Upload costume photo (authenticated, replaces existing if re-uploaded)
  - Headers: `Authorization: Bearer <token>`
  - Body: multipart/form-data with image file
  - Returns: `{costume_id, filename}`
- `DELETE /api/costume` - Delete own costume photo (authenticated)
  - Headers: `Authorization: Bearer <token>`
  - Returns: `{success: true}`
- `GET /api/costumes` - Get all costumes with photo URLs
  - Returns: `[{id, user_id, access_code, photo_url, vote_count}]`

### Voting
- `POST /api/vote` - Submit vote (authenticated, cannot vote for own costume, max `MAX_VOTES_PER_USER` votes total)
  - Headers: `Authorization: Bearer <token>`
  - Body: `{costume_id}`
  - Returns: `{success: true, votes_remaining}` or error if limit reached, duplicate, or voting for self
- `GET /api/results` - Get vote counts and leaderboard
  - Returns: `[{costume_id, access_code, photo_url, vote_count}]` sorted by votes

### Tasks (Optional)
- `GET /api/tasks` - Get user's tasks (authenticated)
- `POST /api/tasks/complete` - Mark task complete with evidence photo

## Frontend Pages

1. **Login Page** (`/login.html`)
   - access_code/password form
   - Store JWT in localStorage on success
   - Redirect to upload page

2. **Upload Page** (`/upload.html`)
   - File input with camera capture
   - Submit photo to backend
   - Option to re-upload/delete if user wants to change photo
   - Redirect to voting page after upload

3. **Voting Page** (`/vote.html`)
   - Grid of all costume photos
   - Click to vote (with confirmation)
   - Show votes remaining (out of `MAX_VOTES_PER_USER`)
   - Disable voting when all votes used
   - Link to results page

4. **Results Page** (`/results.html`)
   - Leaderboard sorted by votes
   - Results hidden until voting is closed (admin control)
   - Auto-refresh every 30 seconds once revealed
   - Show costume photos with vote counts

5. **Tasks Page** (`/tasks.html`) - Optional
   - List of user's tasks
   - Upload evidence photos
   - Mark as complete

## Global Config
- `MAX_VOTES_PER_USER = 5` — single constant used by backend validation and frontend display

## Implementation Notes

### JWT Authentication
- Secret key stored in environment variable
- Token expires in 24 hours (covers party duration)
- Include user_id in token payload
- Verify token on all protected endpoints

### Photo Handling
- Accept JPEG/PNG, max 10MB
- Save to `costumes/` directory with format: `{user_id}_{timestamp}.jpg`
- Optional: Resize to max 1920px width to save space
- Serve as static files via `/static/costumes/{filename}`

### Pre-generated Credentials
- Script to generate N credential pairs (access_code: "guest1", "guest2", etc.)
- Hash passwords before storing
- Print credentials list for distribution at party entrance

### Database
- Use SQLite for simplicity (single file database)
- Create tables on startup if they don't exist
- Consider using SQLAlchemy or raw SQL

### Error Handling
- Return proper HTTP status codes (401 for auth errors, 400 for validation, etc.)
- Consistent error response format: `{error: "message"}`

## Deployment Steps

1. **Deploy**:
   - Push to Railway/Render
   - Set environment variables (JWT_SECRET)
   - Backend serves both API and frontend from single deployment

2. **Pre-party Setup**:
   - Run credential generation script
   - Print/prepare credential list for guests
   - Test full flow end-to-end

## Running Locally

```bash
cd backend
source venv/bin/activate
fastapi dev main.py
```

Credentials are generated automatically on startup from `backend/access_codes.txt`.

## Development Workflow

1. Backend first: Get API endpoints working, test with curl/Postman
2. Frontend pages: Build one page at a time in `frontend/` directory
3. Integration: Test full flow locally (frontend served from same server)
4. Deployment: Single deploy to Railway/Render, test production
5. Optional: Add tasks feature if time permits

## Success Criteria
- Guests can log in with pre-generated credentials
- Guests can upload costume photos from phone
- Guests can vote for up to 5 costumes (not their own, one vote per costume)
- Results page shows live vote counts
- App handles up to 100 concurrent users during party