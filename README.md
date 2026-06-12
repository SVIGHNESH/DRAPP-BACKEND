# Hospital Home-Care System — Backend Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Design (Source Diagrams)](#2-system-design-source-diagrams)
3. [New Feature: Address Support](#3-new-feature-address-support)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Database Schema](#6-database-schema)
7. [API Reference](#7-api-reference)
8. [Authentication](#8-authentication)
9. [Environment Configuration](#9-environment-configuration)
10. [Running the Backend](#10-running-the-backend)
11. [Database Migrations](#11-database-migrations)
12. [Testing](#12-testing)
13. [Code Walkthrough](#13-code-walkthrough)

---

## 1. Project Overview

The Hospital Home-Care System is a booking platform that connects patients (and their relatives) with home-care nursing services. The two actors in the system are:

- **End User / Relative** — authenticates via Google OAuth, browses services, manages family members and saved addresses, and submits booking requests.
- **Admin** — reviews incoming booking requests, arranges a nurse offline (outside the app), and then confirms the booking by recording the nurse details inside the system.

> The **nurse is not a system user**. All admin ↔ nurse coordination happens outside the application. The system only stores the outcome (nurse name + contact) that the admin enters after arranging it.

---

## 2. System Design (Source Diagrams)

The `diagrams/` folder at the repo root contains the full system design in both PlantUML (`.puml`) and Mermaid (embedded in `hospital-homecare-diagrams.md`) formats.

| File | Diagram |
|------|---------|
| `01-context-dfd.puml` | DFD Level 0 — system boundary and external actors |
| `02-dfd-level1.puml` | DFD Level 1 — internal processes and data stores |
| `03-activity.puml` | Activity diagram — booking flow with User / Admin swimlanes |
| `04-sequence.puml` | Sequence diagram — end-to-end request lifecycle |
| `05-er-diagram.puml` | ER diagram — original database schema |

### Booking Status Lifecycle

```
requested → confirmed → in_progress → completed
                                    ↘ cancelled
```

---

## 3. New Feature: Address Support

The original design had no concept of a delivery address. This backend adds first-class address support:

- A user can save **multiple named addresses** on their profile (e.g. "Home", "Mom's place").
- One address can be marked as the **default**.
- When creating a booking the user supplies **exactly one** of:
  - `address_id` — refers to a previously saved address.
  - `custom_address` — a free-text one-off address not saved to the profile.
- The Pydantic schema enforces this constraint at the API layer (providing both, or neither, returns a `422` validation error).

---

## 4. Tech Stack

| Layer | Library / Tool |
|-------|---------------|
| Web framework | FastAPI 0.111 |
| ASGI server | Uvicorn |
| ORM | SQLAlchemy 2.x (async, mapped-column style) |
| Database driver | asyncpg (PostgreSQL) |
| Migrations | Alembic (async env) |
| Schemas / validation | Pydantic v2 |
| Auth — token exchange | httpx (calls Google tokeninfo endpoint) |
| Auth — JWT signing | python-jose |
| Testing | pytest + pytest-asyncio |

---

## 5. Project Structure

```
backend/
├── alembic/
│   ├── env.py              # Async Alembic environment
│   ├── script.py.mako      # Migration file template
│   └── versions/           # Auto-generated migration files live here
├── alembic.ini             # Alembic config (URL overridden at runtime from .env)
├── app/
│   ├── main.py             # FastAPI app factory, router registration
│   ├── config.py           # Pydantic Settings — reads .env
│   ├── database.py         # Async engine, session factory, DeclarativeBase
│   ├── dependencies.py     # get_db, get_current_user, require_admin
│   ├── models/
│   │   ├── __init__.py     # Re-exports all models (needed by Alembic)
│   │   ├── user.py         # User, FamilyMember
│   │   ├── address.py      # Address  ← new
│   │   ├── service.py      # Service
│   │   └── booking.py      # Booking, BookingNote, AssignedNurse
│   ├── schemas/
│   │   ├── user.py         # UserOut, UserUpdate, FamilyMember*
│   │   ├── address.py      # AddressCreate, AddressUpdate, AddressOut
│   │   ├── service.py      # ServiceCreate, ServiceOut
│   │   └── booking.py      # BookingCreate (with address validator), BookingOut, …
│   └── routers/
│       ├── auth.py         # POST /auth/google
│       ├── users.py        # GET/PATCH /users/me
│       ├── family.py       # CRUD /users/me/family-members
│       ├── addresses.py    # CRUD /users/me/addresses  ← new
│       ├── services.py     # GET /services, POST /services (admin)
│       └── bookings.py     # Full booking lifecycle + admin actions
├── tests/
│   └── test_smoke.py       # Schema-level tests (no DB required)
├── requirements.txt
└── .env.example
```

---

## 6. Database Schema

### Entity Relationship (updated)

```
USER ─────────┬──── FAMILY_MEMBER
              │
              ├──── ADDRESS  (new)
              │
              └──── BOOKING ─── BOOKING_NOTE
                         │
                         ├──── ASSIGNED_NURSE
                         │
                         └──── ADDRESS (FK, optional)
```

### Tables

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| `user_id` | int PK | |
| `name` | varchar(255) | |
| `email` | varchar(255) | unique |
| `oauth_provider` | varchar(50) | `"google"` |
| `oauth_id` | varchar(255) | Google `sub` claim |
| `role` | varchar(20) | `"user"` or `"admin"` |
| `created_at` | datetime | server default |

#### `family_members`
| Column | Type | Notes |
|--------|------|-------|
| `member_id` | int PK | |
| `user_id` | int FK → users | cascade delete |
| `name` | varchar(255) | |
| `age` | int | nullable |
| `relation` | varchar(100) | nullable |
| `medical_notes` | varchar(1000) | nullable |

#### `addresses` ← new
| Column | Type | Notes |
|--------|------|-------|
| `address_id` | int PK | |
| `user_id` | int FK → users | cascade delete |
| `label` | varchar(100) | nullable — e.g. "Home" |
| `line1` | varchar(500) | |
| `line2` | varchar(500) | nullable |
| `city` | varchar(100) | |
| `state` | varchar(100) | |
| `pincode` | varchar(20) | |
| `is_default` | boolean | default false |

#### `services`
| Column | Type | Notes |
|--------|------|-------|
| `service_id` | int PK | |
| `name` | varchar(255) | Post-op / Pre-op / Elderly care |
| `description` | text | nullable |
| `base_price` | numeric(10,2) | |
| `active` | boolean | default true |

#### `bookings`
| Column | Type | Notes |
|--------|------|-------|
| `booking_id` | int PK | |
| `user_id` | int FK → users | cascade delete |
| `member_id` | int FK → family_members | nullable, SET NULL on delete |
| `service_id` | int FK → services | |
| `address_id` | int FK → addresses | nullable ← new |
| `custom_address` | varchar(1000) | nullable ← new |
| `slot_start` | datetime | |
| `slot_end` | datetime | |
| `status` | varchar(30) | requested / confirmed / in_progress / completed / cancelled |
| `created_at` | datetime | server default |

#### `booking_notes`
| Column | Type | Notes |
|--------|------|-------|
| `note_id` | int PK | |
| `booking_id` | int FK → bookings | cascade delete |
| `author` | varchar(20) | `"user"` or `"admin"` |
| `message` | text | |
| `created_at` | datetime | server default |

#### `assigned_nurses`
| Column | Type | Notes |
|--------|------|-------|
| `assignment_id` | int PK | |
| `booking_id` | int FK → bookings | unique, cascade delete |
| `nurse_name` | varchar(255) | entered by admin after offline arrangement |
| `nurse_contact` | varchar(100) | nullable |
| `assigned_at` | datetime | server default |

---

## 7. API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Liveness check |

---

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/google` | None | Exchange a Google ID token for a JWT |

**Request body:**
```json
{ "id_token": "<google-id-token>" }
```

**Response:**
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

The endpoint calls `https://oauth2.googleapis.com/tokeninfo` to verify the token, checks the audience against `GOOGLE_CLIENT_ID`, and creates a new user row on first login.

---

### Users

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/me` | User | Get own profile |
| PATCH | `/users/me` | User | Update display name |

**PATCH body:** `{ "name": "Vighnesh Shukla" }`

---

### Addresses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/me/addresses` | User | List all saved addresses |
| POST | `/users/me/addresses` | User | Save a new address |
| PATCH | `/users/me/addresses/{id}` | User | Update an address |
| PATCH | `/users/me/addresses/{id}/set-default` | User | Mark as default |
| DELETE | `/users/me/addresses/{id}` | User | Remove an address |

**POST / PATCH body:**
```json
{
  "label": "Home",
  "line1": "42 MG Road",
  "line2": "Apartment 3B",
  "city": "Bangalore",
  "state": "Karnataka",
  "pincode": "560001",
  "is_default": true
}
```

When `is_default: true` is set, all other addresses for that user are automatically un-defaulted.

---

### Family Members

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/me/family-members` | User | List all members |
| POST | `/users/me/family-members` | User | Add a member |
| PATCH | `/users/me/family-members/{id}` | User | Update a member |
| DELETE | `/users/me/family-members/{id}` | User | Remove a member |

**POST body:**
```json
{
  "name": "Ramesh Shukla",
  "age": 65,
  "relation": "Father",
  "medical_notes": "Diabetic, post knee surgery"
}
```

---

### Services

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/services` | None | List all active services |
| POST | `/services` | Admin | Create a new service |

**POST body:**
```json
{
  "name": "Post-operative Care",
  "description": "Care after a surgical procedure",
  "base_price": 1200.00,
  "active": true
}
```

---

### Bookings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/bookings` | User | Create a booking request |
| GET | `/bookings` | User / Admin | List bookings (admin sees all, user sees own) |
| GET | `/bookings/{id}` | User / Admin | Get booking detail with notes and nurse |
| POST | `/bookings/{id}/notes` | User / Admin | Add a special demand note |
| PATCH | `/bookings/{id}/confirm` | Admin | Confirm booking and record assigned nurse |
| PATCH | `/bookings/{id}/status` | Admin | Update booking status |

**POST `/bookings` body:**
```json
{
  "service_id": 1,
  "member_id": 2,
  "slot_start": "2026-06-20T08:00:00",
  "slot_end": "2026-06-20T20:00:00",
  "address_id": 3,
  "custom_address": null,
  "notes": "Patient is allergic to latex gloves"
}
```

> Exactly one of `address_id` or `custom_address` must be provided. Providing both or neither returns `422 Unprocessable Entity`.

**PATCH `/bookings/{id}/confirm` body (Admin):**
```json
{
  "nurse_name": "Priya Mehta",
  "nurse_contact": "+91-9876543210"
}
```

**PATCH `/bookings/{id}/status` body (Admin):**
```json
{ "status": "in_progress" }
```

Valid statuses: `requested`, `confirmed`, `in_progress`, `completed`, `cancelled`.

---

## 8. Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header:

```
Authorization: Bearer <jwt>
```

Tokens are issued by `POST /auth/google` and expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 1440 = 24 hours).

**JWT payload:**
```json
{ "sub": "<user_id>", "exp": <unix_timestamp> }
```

**Role-based access:**
- `get_current_user` — any authenticated user.
- `require_admin` — user whose `role` column is `"admin"`. To promote a user to admin, update the `role` column directly in the database (no admin-management endpoint is exposed).

---

## 9. Environment Configuration

Copy `.env.example` to `.env` and fill in the values:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/drapp
SECRET_KEY=change-me-to-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Async PostgreSQL URL — must use `postgresql+asyncpg://` scheme |
| `SECRET_KEY` | Random secret used to sign JWTs — keep this private |
| `ALGORITHM` | JWT signing algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL in minutes |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console — OAuth 2.0 Client ID |

---

## 10. Running the Backend

### Prerequisites

- Python 3.11+
- PostgreSQL running and accessible
- A Google OAuth 2.0 Client ID

### Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL, secret key, and Google client ID

# Run migrations (creates all tables)
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

The API is now available at `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

---

## 11. Database Migrations

Alembic is configured for async PostgreSQL. The `alembic/env.py` reads `DATABASE_URL` from `.env` automatically.

```bash
# Apply all pending migrations
alembic upgrade head

# Generate a new migration after changing models
alembic revision --autogenerate -m "describe the change"

# Roll back one migration
alembic downgrade -1

# View current revision
alembic current

# View migration history
alembic history
```

> Always review auto-generated migrations before applying them — Alembic cannot detect column renames or some constraint changes automatically.

---

## 12. Testing

The smoke test suite validates schema-level logic without requiring a database.

```bash
cd backend
source .venv/bin/activate

# Set minimal env vars (real DB not needed for smoke tests)
export DATABASE_URL=postgresql+asyncpg://x:x@localhost/x
export SECRET_KEY=test
export GOOGLE_CLIENT_ID=test

pytest tests/ -v
```

**Current tests:**

| Test | What it checks |
|------|---------------|
| `test_booking_requires_exactly_one_address` | `BookingCreate` rejects both/neither address, accepts one |

---

## 13. Code Walkthrough

### `app/config.py`
Pydantic `BaseSettings` class that reads all configuration from environment variables (or `.env`). Imported as a singleton `settings` used across the app.

### `app/database.py`
Creates the SQLAlchemy async engine and `AsyncSessionLocal` session factory. `Base` is the `DeclarativeBase` all models inherit from.

### `app/dependencies.py`
Three FastAPI dependency functions:
- `get_db` — yields an `AsyncSession`, used by every router.
- `get_current_user` — decodes the Bearer JWT, loads the `User` row. Raises `401` on any failure.
- `require_admin` — calls `get_current_user` and additionally checks `role == "admin"`. Raises `403` otherwise.

### `app/models/`
All SQLAlchemy models use the modern **mapped-column** style (`Mapped[T]`, `mapped_column()`). Relationships are declared with `relationship()` and `selectinload` is used in routers to avoid N+1 queries on nested objects.

### `app/schemas/booking.py` — Address Constraint
The `@model_validator(mode="after")` on `BookingCreate` enforces the address rule:

```python
@model_validator(mode="after")
def validate_address(self):
    has_saved = self.address_id is not None
    has_custom = self.custom_address is not None and self.custom_address.strip() != ""
    if has_saved == has_custom:   # both True or both False → error
        raise ValueError("Provide exactly one of address_id or custom_address")
    return self
```

### `app/routers/addresses.py` — Default Address Logic
When an address is set as default (either via `POST` with `is_default: true`, `PATCH`, or the dedicated `set-default` endpoint), the router first issues an `UPDATE` to clear `is_default = false` for all existing addresses of that user, then sets the target address to `true`. This ensures only one default ever exists.

### `app/routers/bookings.py` — Admin Confirm Flow
`PATCH /bookings/{id}/confirm` follows the sequence diagram: admin records the nurse details after arranging offline. It upserts into `assigned_nurses` (creates a new row or updates existing) and sets `booking.status = "confirmed"`.

### `alembic/env.py`
Configured for async migrations using `async_engine_from_config`. The `app.models` package is imported to register all `Base` subclasses with `target_metadata = Base.metadata` so Alembic can detect the full schema.
