from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware  # BẬT NÉN GZIP
import os

from routers import rooms, tenants, contracts, bills, electric, dashboard, invoice, auth, accounts
from core.security import decrypt_value
from core.deps import get_db
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

app = FastAPI(title="Rental Management Dashboard")

# Kích hoạt nén GZip cho các Response lớn hơn 1000 bytes (Giảm 70% dung lượng mạng)
app.add_middleware(GZipMiddleware, minimum_size=1000)

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

    try:
        sess_ua = session_doc.get('user_agent')
        if sess_ua:
            req_ua = request.headers.get('user-agent','')
            if sess_ua != req_ua:
                return RedirectResponse(url="/login", status_code=303)
    except Exception:
        pass

    request.state.user = account
    request.state.user_role = account.get("role", "user")
    try:
        request.state.csrf_token = session_doc.get('csrf_token')
    except Exception:
        request.state.csrf_token = None

    unsafe_methods = ("POST", "PUT", "PATCH", "DELETE")
    if request.method in unsafe_methods:
        try:
            session_csrf = session_doc.get('csrf_token')
            content_type = request.headers.get('content-type', '')
            token_match = False

            header_token = request.headers.get('x-csrf-token') or request.headers.get('x-xsrf-token')
            if header_token and session_csrf and header_token == session_csrf:
                token_match = True
                return await call_next(request)

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

                async def receive():
                    return {"type": "http.request", "body": body, "more_body": False}

                if not token_match:
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"detail": "CSRF token missing or invalid"}, status_code=403)

                new_request = Request(request.scope, receive)
                return await call_next(new_request)

            if not token_match:
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "CSRF token missing or invalid"}, status_code=403)
        except Exception:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)

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
    from core.security import _get_fernet

    if _get_fernet() is None:
        msg = "DATA_ENCRYPTION_KEY is not configured or cryptography missing. Exiting for security."
        logger.error(msg)
        raise RuntimeError(msg)

    # TỰ ĐỘNG ĐÁNH INDEX KHI KHỞI ĐỘNG SERVER (Tăng tốc độ truy vấn lên gấp nhiều lần)
    try:
        db = get_db()
        await db.sessions.create_index([("expires_at", 1)], expireAfterSeconds=0, name="sessions_expires_at_ttl")
        
        # Đánh Index cho các truy vấn phổ biến
        await db.bills.create_index([("month", -1), ("status", 1)])
        await db.electric_readings.create_index([("room_id", 1), ("month", -1)])
        await db.contracts.create_index([("room_id", 1), ("tenant_id", 1)])
        logger.info("⚡ MongoDB Indexes đã được tối ưu hóa!")
    except Exception as e:
        logger.exception("Failed to ensure indexes: %s", e)

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
    return JSONResponse(content={})