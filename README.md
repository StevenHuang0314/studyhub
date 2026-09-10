# StudyHub

A full-stack study resource and study-group app for CS students. Students post
course notes, rate each other's resources, and form study groups with limited
seats.

**Stack:** FastAPI · SQLAlchemy 2.0 · SQLite/Postgres · JWT auth · React 18 · TypeScript · Vite

---

## What it does

| Feature | Details |
| --- | --- |
| Accounts | Register / sign in, JWT bearer tokens, bcrypt password hashing, editable profile |
| Notes (CRUD) | Post, browse, edit and delete course notes; only the author can modify their own |
| Search & filter | Full-text-ish search on title and body, filter by course code or tag, four sort orders, paginated |
| Ratings | 1–5 stars with an optional comment; one rating per user per note, enforced in the database; you can't rate your own note |
| Study groups (CRUD) | Create, edit and delete groups; join and leave; capacity limits enforced server-side; the owner can't silently abandon a group |
| Dashboard | Your notes, your groups, and aggregate stats on the reviews you've received |

## Screens

- `/notes` — browse, search, filter and sort shared notes
- `/notes/:id` — read a note, leave or update a review
- `/groups` — browse groups, filter to ones with space left
- `/groups/:id` — group details, member list, join/leave
- `/dashboard` — your own notes and groups

---

## Running it locally

Two terminals: one for the API, one for the web client.

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m app.seed                # optional: demo users, notes and groups
uvicorn app.main:app --reload
```

API: <http://127.0.0.1:8000> · Interactive docs: <http://127.0.0.1:8000/docs>

Every seeded account uses the password `password123` — try `ada@wisc.edu`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: <http://localhost:5173>. Vite proxies `/api` to the backend, so there's no
CORS setup to do in development.

### 3. Tests

```bash
cd backend
pytest                # 50 tests covering auth, ownership, CRUD and rating rules

cd ../frontend
npm run typecheck     # tsc --noEmit
npm run build         # production bundle
```

GitHub Actions runs all three on every push (`.github/workflows/ci.yml`).

---

## API

All endpoints are under `/api`. Protected routes need `Authorization: Bearer <token>`.

### Auth

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Create an account, returns a token |
| `POST` | `/api/auth/login` | JSON login, returns a token |
| `POST` | `/api/auth/token` | OAuth2 form login (powers the Swagger **Authorize** button) |
| `GET` | `/api/auth/me` | Current user |
| `PATCH` | `/api/auth/me` | Update username or bio |

### Notes

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/notes` | List with `search`, `course_code`, `tag`, `author_id`, `sort`, `skip`, `limit` |
| `POST` | `/api/notes` | Create (auth) |
| `GET` | `/api/notes/{id}` | One note, with average rating |
| `PATCH` | `/api/notes/{id}` | Update (author only) |
| `DELETE` | `/api/notes/{id}` | Delete (author only) |
| `GET` | `/api/notes/courses` | Distinct course codes, for filter menus |

### Ratings

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/notes/{id}/ratings` | All reviews for a note |
| `PUT` | `/api/notes/{id}/ratings` | Create **or** replace your rating — idempotent, hence `PUT` |
| `DELETE` | `/api/notes/{id}/ratings/me` | Remove your rating |

### Study groups

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/groups` | List with `search`, `course_code`, `has_space` |
| `POST` | `/api/groups` | Create (creator joins automatically) |
| `GET` | `/api/groups/{id}` | One group with its member list |
| `PATCH` | `/api/groups/{id}` | Update (owner only) |
| `DELETE` | `/api/groups/{id}` | Delete (owner only) |
| `POST` | `/api/groups/{id}/members` | Join |
| `DELETE` | `/api/groups/{id}/members/me` | Leave |

### Users

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/users/me/notes` | Your notes |
| `GET` | `/api/users/me/groups` | Groups you own or joined |
| `GET` | `/api/users/{id}` | Public profile |
| `GET` | `/api/users/{id}/notes` | Someone's notes |

---

## Data model

```
User ──< Note ──< Rating >── User
 │                             
 └──< GroupMembership >── StudyGroup ──> User (owner)
```

- `ratings` has a unique constraint on `(note_id, user_id)` and a check
  constraint keeping `score` between 1 and 5 — the "one rating per user" rule
  is enforced by the database, not just by application code.
- `group_memberships` has a unique constraint on `(group_id, user_id)`.
- Deleting a note deletes its ratings; deleting a group deletes its memberships.

## Design notes

A few decisions worth calling out, since they're the kind of thing that comes up
in an interview:

- **`PUT` for ratings, not `POST`.** A user has at most one rating per note, so
  submitting the same rating twice should leave the same state. That's the
  definition of idempotent, which is what `PUT` is for.
- **Average ratings are computed in SQL,** via a `GROUP BY` subquery joined onto
  the note list, rather than loading every rating into Python. That keeps the
  list endpoint at a constant number of queries as the data grows, and it's what
  makes `sort=top_rated` possible in the database.
- **Ownership is checked in one place per resource** (`_require_author`,
  `_require_owner`) so authorization can't drift between endpoints.
- **Login timing is constant-ish.** An unknown email still runs a bcrypt
  comparison against a dummy hash, so response time doesn't reveal which
  accounts exist.
- **Schemas are separate from models.** The API contract is explicit: password
  hashes can't leak into a response and clients can't set `author_id` by
  sending it.
- **SQLite by default, Postgres-ready.** Change `DATABASE_URL` and nothing else
  has to change; a production deployment would swap `create_all()` for Alembic
  migrations.

## Project layout

```
backend/
  app/
    main.py          FastAPI app, CORS, router wiring
    config.py        Settings from environment / .env
    database.py      Engine, session factory, declarative base
    models.py        SQLAlchemy models and constraints
    schemas.py       Pydantic request/response models
    security.py      Password hashing and JWT
    deps.py          Shared dependencies (DB session, current user)
    seed.py          Demo data
    routers/         auth, notes (+ ratings), groups, users
  tests/             pytest suite
frontend/
  src/
    api/client.ts    Typed fetch wrapper
    context/         Auth provider
    components/      Navbar, cards, star rating, route guard
    pages/           Notes, groups, auth, dashboard
```

## Possible next steps

File uploads for note attachments, comment threads on notes, group join
requests with owner approval, and moving from `create_all()` to Alembic
migrations.
