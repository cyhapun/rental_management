from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import os

from routers import rooms, tenants, contracts, bills, electric, dashboard, invoice, auth, accounts
from core.security import decrypt_value
from core.deps import get_db
from datetime import datetime
import logging
import asyncio


logger = logging.getLogger(__name__)

app = FastAPI(title="Rental Management Dashboard")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.include_router(auth)
app.include_router(dashboard)
app.include_router(rooms)
app.include_router(tenants)
app.include_router(contracts)
app.include_router(bills)
app.include_router(electric)
app.include_router(invoice)
app.include_router(accounts)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path or "/"
    public_prefixes = ("/login", "/logout", "/static", "/.well-known")
    if path.startswith(public_prefixes):
        return await call_next(request)

    # Use an encrypted session cookie which maps to a server-side session record.
    cookie_name = os.getenv("SESSION_COOKIE_NAME", "rental_session")
    session_cookie = request.cookies.get(cookie_name)
    if not session_cookie:
        return RedirectResponse(url="/login", status_code=303)

    try:
        session_id = decrypt_value(session_cookie)
    except Exception:
        return RedirectResponse(url="/login", status_code=303)

    db = get_db()
    now = datetime.utcnow()
    session_doc = await db.sessions.find_one({"_id": session_id, "expires_at": {"$gt": now}})
    if not session_doc:
        return RedirectResponse(url="/login", status_code=303)

    account = await db.accounts.find_one({"_id": session_doc.get("user_id")})
    if not account:
        return RedirectResponse(url="/login", status_code=303)

    # Optional: verify user-agent/ip fingerprint if recorded on session
    try:
        sess_ua = session_doc.get('user_agent')
        if sess_ua:
            req_ua = request.headers.get('user-agent','')
            if sess_ua != req_ua:
                return RedirectResponse(url="/login", status_code=303)
    except Exception:
        pass

    # Keep backward-compatible `user_role` for templates that expect it.
    request.state.user = account
    request.state.user_role = account.get("role", "user")
    # expose csrf token to templates from server-side session (do NOT store readable cookie)
    try:
        request.state.csrf_token = session_doc.get('csrf_token')
    except Exception:
        request.state.csrf_token = None

    # CSRF protection (double-submit pattern + server-side token verification)
    # For unsafe methods, verify token from header or form matches session's csrf_token.
    unsafe_methods = ("POST", "PUT", "PATCH", "DELETE")
    if request.method in unsafe_methods:
        # Allow public endpoints to manage their own checks
        # Try header first (for AJAX/JSON clients)
        try:
            session_csrf = session_doc.get('csrf_token')
            content_type = request.headers.get('content-type', '')
            token_match = False

            # check JSON/AJAX header
            header_token = request.headers.get('x-csrf-token') or request.headers.get('x-xsrf-token')
            if header_token and session_csrf and header_token == session_csrf:
                token_match = True
                return await call_next(request)

            # For form submissions, we need to read the body to extract csrf_token
            if 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
                body = await request.body()
                try:
                    from urllib.parse import parse_qs

                    params = parse_qs(body.decode('utf-8', errors='ignore'))
                    form_token = params.get('csrf_token', [None])[0]
                except Exception:
                    form_token = None

                if form_token and session_csrf and form_token == session_csrf:
                    token_match = True

                # recreate request for downstream since body consumed
                async def receive():
                    return {"type": "http.request", "body": body, "more_body": False}

                if not token_match:
                    from fastapi.responses import JSONResponse

                    return JSONResponse({"detail": "CSRF token missing or invalid"}, status_code=403)

                new_request = Request(request.scope, receive)
                return await call_next(new_request)

            # If not form/json, reject if header not present
            if not token_match:
                from fastapi.responses import JSONResponse

                return JSONResponse({"detail": "CSRF token missing or invalid"}, status_code=403)
        except Exception:
            # On any error in CSRF checking, reject request for safety
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)

    # Only /accounts should be admin-only; managers have access to other pages
    admin_only_prefixes = ("/accounts",)
    if path.startswith(admin_only_prefixes) and request.state.user_role != "admin":
        if request.method != "GET":
            return JSONResponse({"detail": "Bạn không có quyền hạn để thấy"}, status_code=403)
        return RedirectResponse(
            url="/dashboard?flash=Bạn%20không%20có%20quyền%20hạn%20để%20thấy&level=warning",
            status_code=303,
        )

    return await call_next(request)


@app.on_event("startup")
async def on_startup():
    # Strict startup checks for security-critical configuration
    from core.security import _get_fernet

    if _get_fernet() is None:
        # DATA_ENCRYPTION_KEY must be set in production (raises to avoid insecure fallback)
        msg = "DATA_ENCRYPTION_KEY is not configured or cryptography missing. Exiting for security."
        logger.error(msg)
        raise RuntimeError(msg)

    # Ensure sessions collection has a TTL index on expires_at
    try:
        db = get_db()
        # expire documents at the time in `expires_at`
        await db.sessions.create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            name="sessions_expires_at_ttl",
        )
        logger.info("Ensured TTL index on sessions.expires_at")
    except Exception as e:
        logger.exception("Failed to ensure sessions TTL index: %s", e)
        # Not critical enough to stop startup, but we log it.

    # Auto-create an initial admin account if none exists (convenience for first-run).
    try:
        existing = await db.accounts.find_one({})
        if not existing:
            from core.security import hash_password

            default_username = "chauhuynhphuc"
            default_password = "cyhapun"
            pw_hash = hash_password(default_password)
            acct = {
                "username": default_username,
                "password": pw_hash,
                "role": "admin",
                "created_at": datetime.utcnow(),
            }
            await db.accounts.insert_one(acct)
            logger.warning("Created initial admin account: %s", default_username)
            logger.warning("Please delete or change this account after first login.")
    except Exception:
        logger.exception("Failed to auto-create initial account")


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_probe():
    # Chrome DevTools makes this request automatically in some environments.
    return JSONResponse(content={})
