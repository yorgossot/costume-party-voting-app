# Frontend — Costume Party App

## Quick Start

The frontend is served by the FastAPI backend. No build step needed.

```bash
cd backend
source venv/bin/activate
python generate_credentials.py 20   # first time only
fastapi dev main.py
```

Then open `http://localhost:8000` on your phone or browser.

---

## Architecture

This is a **single-page app (SPA)** built with vanilla HTML, CSS, and JavaScript — no frameworks, no build tools.

Everything runs from one `index.html` file. Each "page" is a `<div class="view">` that gets shown/hidden by the router in `app.js`. This means **zero page reloads** when navigating between views.

### How navigation works

```
App.navigate('vote')
  → hides all .view divs
  → shows #view-vote
  → shows/hides the tab bar
  → calls Vote.onEnter() to fetch data and render
```

The bottom tab bar has 3 tabs (Me, Vote, Results) plus a 4th Admin tab that only appears for admin users.

---

## File Structure

```
frontend/
├── index.html          ← App shell: all views, tab bar, modals, script tags
├── manifest.json       ← PWA manifest (enables "Add to Home Screen")
├── css/
│   └── styles.css      ← All styles, mobile-first
└── js/
    ├── utils.js        ← Helpers: toast notifications, loading overlay, confirm dialog, image resize
    ├── api.js          ← API client: all fetch calls, token management, auto-logout on 401
    ├── auth.js         ← Login view: form handler, token storage
    ├── setup.js        ← Setup wizard: 3-step flow (name → costume desc → photo upload)
    ├── vote.js         ← Voting view: costume grid, vote/unvote, photo modal
    ├── results.js      ← Results view: leaderboard, locked state, auto-refresh
    ├── admin.js        ← Admin view: toggle voting, toggle result visibility
    └── app.js          ← Router, initialization, Home view module
```

### Script load order matters

Scripts load in this order (defined in `index.html`):

1. **utils.js** — standalone helpers, no dependencies
2. **api.js** — defines `API` object (references `App` only at runtime, not at load)
3. **auth.js** — defines `Auth` object
4. **setup.js** — defines `Setup` object
5. **vote.js** — defines `Vote` object
6. **results.js** — defines `Results` object
7. **admin.js** — defines `Admin` object
8. **app.js** — defines `App` + `Home`, runs `App.init()` on DOMContentLoaded (last, so all modules exist)

Each module is a plain object on `window` (e.g., `var Vote = { ... }`). They reference each other at **runtime** (inside event handlers), not at **load time**, so the order works fine.

---

## How Each Module Works

### `api.js` — API Client

All backend communication goes through the `API` object. Example:

```js
API.vote(costumeId)         // POST /api/vote
API.getCostumes()           // GET /api/costumes
API.uploadCostume(file)     // POST /api/upload-costume (multipart)
```

- JWT token stored in `localStorage` and sent as `Authorization: Bearer <token>`
- On any **401 response**, automatically clears token and redirects to login
- Errors throw `{ status, detail }` — the `detail` string comes from the backend

### `app.js` — Router & Home

The `App` object is the central controller:

- `App.init()` — checks for existing token, fetches `/api/me`, routes to the right view
- `App.navigate(viewName)` — switches views, calls `onLeave()` on old view and `onEnter()` on new view
- `App.routeAfterAuth()` — decides whether to show setup wizard or main app
- `App.user` — cached user state from `/api/me`

`Home` is also defined here (to avoid an extra file). It shows the user's costume with re-upload and delete options.

### `auth.js` — Login

Handles the login form submission. On success, stores the JWT and calls `App.routeAfterAuth()`.

### `setup.js` — Setup Wizard

A 3-step wizard that runs after first login:

1. **Display name** — text input, 4-30 chars, immutable after set
2. **Dressed up as** — costume description, same rules
3. **Photo upload** — camera capture on mobile, preview before upload

The wizard detects which steps are already complete (from `App.user`) and skips them. After all 3 steps, navigates to the vote view.

### `vote.js` — Voting Grid

The main feature. Renders a 2-column grid of costume photos with:

- Heart button overlay for voting/unvoting (tap toggles)
- "You" badge on your own costume
- Votes-remaining counter in the header
- Tap a photo → full-screen modal with vote button
- Auto-refreshes every 30 seconds to pick up new costumes
- Handles "voting closed" state

### `results.js` — Leaderboard

Two states:
- **Locked** (403 from API) — shows "Results coming soon" message
- **Visible** — ranked list with gold/silver/bronze medals for top 3, vote count bars

Auto-refreshes every 15 seconds.

### `admin.js` — Admin Controls

Only accessible to admin users. Two toggle switches:
- **Voting** — open/close voting
- **Results** — show/hide results

---

## CSS Organization (`styles.css`)

The CSS is organized in sections (marked with comments):

| Section | What it styles |
|---------|---------------|
| Reset & Base | Box-sizing, colors, CSS variables, body |
| Utility | `.hidden` class |
| Views | `.view`, `.view-header` positioning |
| Tab Bar | Bottom navigation bar |
| Buttons | `.btn`, `.btn-primary`, `.btn-icon`, etc. |
| Inputs | Text inputs, `.input-group`, `.char-counter` |
| Forms | `.form-stack`, `.error-text` |
| Login | `.center-container`, `.login-hero` |
| Setup Wizard | `.progress-dots`, `.setup-step`, `.upload-area` |
| Costume Grid | `.costume-grid`, `.costume-card`, `.vote-btn` |
| Banner | Warning banners (voting closed) |
| Photo Modal | Full-screen photo viewer |
| Home View | User's costume card |
| Results | Leaderboard rows, medals, vote bars |
| Admin | Toggle switches, admin cards |
| Toast | Toast notification popups |
| Loading | Spinner overlay |
| Animations | Keyframes (spin, heartPop, toastIn/Out) |
| Tablet+ | `@media (min-width: 768px)` overrides |

### CSS Variables (`:root`)

All colors and sizes are defined as CSS variables at the top. To change the theme, edit these:

```css
--bg: #1a1a2e;           /* Page background */
--surface: #16213e;       /* Card/tab bar background */
--primary: #e94560;       /* Accent color (hearts, buttons) */
--gradient: linear-gradient(135deg, #e94560, #8b5cf6);  /* Button gradient */
```

### Mobile-first approach

- Base styles target phones (no media queries)
- 16px font on inputs prevents iOS auto-zoom
- 48px minimum touch targets on all interactive elements
- `env(safe-area-inset-*)` handles notched phones (iPhone X+)
- `overscroll-behavior-y: contain` prevents pull-to-refresh in Chrome

---

## User Flow

```
Login → Setup Wizard (3 steps) → Vote Grid ←→ Results
                                     ↕
                                   Home (manage costume)
                                     ↕
                                   Admin (if admin user)
```

1. Open app → if no token, show **Login**
2. After login → if setup incomplete, show **Setup Wizard**
3. After setup → land on **Vote** grid
4. **Tab bar** lets you switch between Me / Vote / Results / Admin
5. **Home** (Me tab) shows your costume, lets you re-upload or delete
6. **Results** shows leaderboard when admin reveals it

---

## Adding a New View

1. Add a `<div id="view-myview" class="view tab-view hidden">` in `index.html`
2. Create `js/myview.js` with a module object that has `onEnter()` and optionally `onLeave()`
3. Add a `<script>` tag in `index.html` (before `app.js`)
4. Register it in `App.views` in `app.js`
5. Add a tab button in the `#tab-bar` nav (or navigate to it programmatically)

---

## PWA Support

The `manifest.json` enables "Add to Home Screen" on Android and iOS. When installed:
- App runs in standalone mode (no browser chrome)
- Background color matches the dark theme
- Portrait orientation locked

To install: open the app in Chrome/Safari → menu → "Add to Home Screen".
