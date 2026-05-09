# Rental Management Dashboard

This repository contains a compact Rental Management Dashboard web application built in Python using FastAPI and MongoDB. It provides basic functionality to manage rooms, tenants, rental contracts, electricity/water readings, bills/invoices, and exportable reports (PDF/Excel).

This README documents the project's architecture, technology stack, directory layout, required environment variables, run and maintenance instructions, and recommended next steps for development and deployment.

---

## Key Features

- Web UI using server-rendered Jinja2 templates for fast, simple dashboards.
- Asynchronous backend powered by FastAPI and `motor` (async MongoDB driver).
- Session management with encrypted cookies and CSRF protection.
- Secure password storage using PBKDF2-HMAC-SHA256.
- Bill/invoice generation (Excel/PDF) using `pandas`, `weasyprint`, and `reportlab`.
- Utility scripts for inspecting and normalizing bills; async implementations available.
- Automatic MongoDB index creation on startup for common queries.

---

## Technology Stack

- Language: Python 3.10+ (async-first code in FastAPI)
- Web framework: FastAPI
- ASGI server: uvicorn
- Database: MongoDB (async access via `motor`, some scripts historically used `pymongo`)
- Template engine: Jinja2
- Background / heavy output: `pandas`, `openpyxl`, `weasyprint`, `reportlab`
- Crypto: `cryptography` (Fernet) for field encryption; PBKDF2 via Python `hashlib` for password hashing
- Environment config: `python-dotenv`
- Client-side: plain JavaScript + CSS under `static/` and server-rendered pages in `templates/`

---

## Directory Structure and Purpose

Top-level layout (paths are relative to project root):

- `main.py` — application entrypoint. Creates the `FastAPI` app, mounts static files, registers routers, and includes the authentication/session middleware and startup tasks (indexes, initial admin account creation).

- `requirements.txt` — Python dependencies necessary to run the project.

- `vercel.json` — deployment configuration for Vercel (if used).

- `core/` — foundational helpers and utilities used across the app:
  - `core/deps.py` — database dependency (`get_db()`) and other dependency helpers.
  - `core/security.py` — hashing (`hash_password`, `verify_password`), Fernet encryption helpers (`encrypt_value`, `decrypt_value`), session id generation, and tenant document helpers (`tenant_doc_to_ui`). The app expects `DATA_ENCRYPTION_KEY` for Fernet.
  - `core/flash.py` — helper for redirect-with-flash messaging used in templates.
  - `core/template_filters.py` — Jinja2 template filters used by the UI.
  - `core/constants.py` — shared constants used across the app.

- `routers/` — FastAPI route modules, each exposing CRUD and UI endpoints for a domain:
  - `routers/auth.py` — login/logout and authentication endpoints.
  - `routers/accounts.py` — admin account management (admin-only routes).
  - `routers/dashboard.py` — dashboard landing page and summary endpoints.
  - `routers/rooms.py` — room CRUD, lookup by room number.
  - `routers/tenants.py` — tenant CRUD and tenant listing (includes `/_list` JSON endpoint for AJAX consumption).
  - `routers/contracts.py` — contract lifecycle and logic for due dates / rent cycles.
  - `routers/bills.py` — bills listing and payment state changes.
  - `routers/electric.py` — electric readings ingestion and lookup.
  - `routers/invoice.py` — invoice printing and PDF rendering endpoints.

- `schemas/` — Pydantic schemas used for request/response validation and typed models.

- `scripts/` — utility and maintenance scripts. There are async script implementations (using `motor`) alongside small synchronous wrapper scripts preserved for CLI compatibility. Important scripts:
  - `scripts/create_bill_from_reading_async.py` and wrapper `scripts/create_bill_from_reading.py` — create a bill from latest electric reading for a contract.
  - `scripts/inspect_bill_async.py` and wrapper `scripts/inspect_bill.py` — inspect contracts, bills, readings for troubleshooting.
  - `scripts/normalize_bills_async.py` and wrapper `scripts/normalize_bills.py` — backfill/normalize bill fields and totals.
  - Note: wrappers call the async implementations to preserve the original CLI interface (no logic change).

- `templates/` — Jinja2 templates for server-rendered pages. Examples: `tenants.html`, `rooms.html`, `bills.html`, `dashboard.html`, `invoice_print.html`, and partials under `templates/partials/`.

- `static/` — static assets (CSS, JS, images) served at `/static`.

---

## Important Files and Behaviour Notes

- `main.py`
  - Registers routers and mounts `StaticFiles` at `/static`.
  - Adds a GZip middleware to compress large responses.
  - Implements a `http` middleware to validate encrypted session cookies and CSRF tokens for unsafe methods.
  - On startup, ensures MongoDB indexes for `sessions`, `bills`, `electric_readings`, and `contracts` and will auto-create a default admin account if the `accounts` collection is empty (this behavior is intended for convenience in development — change or remove for production).

- `core/security.py`
  - Uses `DATA_ENCRYPTION_KEY` (Fernet) to encrypt/decrypt sensitive fields (phone, national id). If the key is missing and `cryptography` is unavailable, encryption falls back to storing plaintext — the code intentionally requires the key at startup and will raise an error.
  - Implements `hash_password` / `verify_password` using `hashlib.pbkdf2_hmac`.

- `scripts/*_async.py` (new files)
  - Re-implemented maintenance scripts with `motor.motor_asyncio.AsyncIOMotorClient` to be consistent with the async app.
  - The original script filenames (without `_async`) were replaced with small wrappers that import and run the async implementation so existing CLI usage remains unchanged.

---

## Environment Variables

Create a `.env` file in the project root (do NOT commit secrets). Required variables (minimum):

- `MONGO_URI` — MongoDB connection URI (e.g. `mongodb://localhost:27017`).
- `MONGO_DB` — database name used by the app.
- `DATA_ENCRYPTION_KEY` — base64-encoded 32-byte key for Fernet (required for startup). Example: `F0rExAmplEBase64Key...` (generate securely).

Optional/Useful environment variables:

- `SESSION_COOKIE_NAME` — name of the session cookie (default `rental_session`).
- `PRICE_PER_KWH` — default price per kWh (fallback when reading missing). Example: `3000`.
- `WATER_FEE` — default water fee per month (fallback): e.g. `50000`.
- `APP_URL` — application URL (used when contacting external APIs or for headers).

Security note: store `DATA_ENCRYPTION_KEY` and any API credentials in a secrets manager (Vault, GitHub Secrets, environment variables in cloud) — do not commit to git.

---

## Local Development — Quick Start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv/Scripts/activate
pip install -r requirements.txt
```

2. Add a `.env` file at the project root with the required variables (see section above).

3. Start MongoDB (local or remote) and ensure `MONGO_URI` is reachable.

4. Run the development server from the project root:

```bash
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/dashboard or /login in your browser.

Notes:
- On first run (if `accounts` collection is empty) the app will automatically insert a default admin user with username `admin` and password `password` — change this immediately in dev/production.
- The app will create helpful MongoDB indexes during startup for better query performance.

---

## CLI Scripts (maintenance)

Scripts are stored in `scripts/`. Historically some scripts used `pymongo`; they have been reimplemented with `motor` (async) and the original filenames preserved as thin wrappers to maintain CLI compatibility.

Usage (examples):

```bash
# Create a bill automatically from the latest electric reading for a contract
python scripts/create_bill_from_reading.py <contract_id> [YYYY-MM]

# Inspect contract/bill/reading details for debugging
python scripts/inspect_bill.py <contract_id_or_room_id>

# Normalize/backfill bill fields (room_price, electric_cost, total)
python scripts/normalize_bills.py <identifier>
```

Run these scripts as separate CLI processes (do NOT call them inside the FastAPI event loop). The wrappers will call async implementations internally.

---

## Security & Operational Notes

- Keep `DATA_ENCRYPTION_KEY` secret and rotate if leaked.
- Remove or change the automatic default admin account behavior for production.
- Keep the app behind HTTPS in production.
- Avoid running synchronous blocking operations inside request handlers — heavy CPU tasks (PDF rendering, Excel generation) should be offloaded to background workers or run asynchronously to avoid blocking the event loop.

---

File reference: main entrypoint is [main.py](main.py#L1).
