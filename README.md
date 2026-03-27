# Rental Management Dashboard

Rental Management Dashboard is a small FastAPI application for managing rooms, tenants, contracts, utilities, and invoices for rental properties.

Highlights:
- Built with FastAPI and MongoDB (Motor).
- Secure password storage (PBKDF2-HMAC-SHA256) and server-side sessions with encrypted cookies.
- Intended to run behind HTTPS (Vercel or similar).

Quick start:

1. Configure environment variables: `MONGO_URI`, `MONGO_DB`, and `DATA_ENCRYPTION_KEY`.
2. Create an initial account:

```bash
python app/scripts/create_account.py admin YourStrongPassword admin
```

3. Run the app locally:

```bash
uvicorn app.main:app --port 8000
```