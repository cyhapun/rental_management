from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import RedirectResponse
import os
from datetime import datetime, timedelta

from deps import get_db
from security import encrypt_value, verify_password, generate_session_id

router = APIRouter()


@router.get('/login')
async def login_get(request: Request):
    from fastapi.templating import Jinja2Templates
    import os as _os
    templates = Jinja2Templates(directory=_os.path.join(_os.path.dirname(__file__), '..', 'templates'))
    resp = templates.TemplateResponse(request=request, name='login.html', context={})
    # Clear session cookie if user navigates to login explicitly
    try:
        cookie_name = __import__('os').getenv('SESSION_COOKIE_NAME', 'rental_session')
        resp.delete_cookie(cookie_name, path='/')
    except Exception:
        pass
    return resp


@router.post('/login')
async def login_post(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    # Authenticate against `account` collection in DB.
    db = get_db()
    acct = await db.accounts.find_one({"username": username})
    if not acct:
        return RedirectResponse(url='/login', status_code=303)

    stored_password = acct.get("password") or ""
    if not verify_password(stored_password, password):
        return RedirectResponse(url='/login', status_code=303)

    # Create a server-side session and set an encrypted session cookie.
    session_id = generate_session_id()
    now = datetime.utcnow()
    expires = now + timedelta(hours=8)
    session_doc = {
        "_id": session_id,
        "user_id": acct.get("_id"),
        "created_at": now,
        "expires_at": expires,
        # bind user agent and remote address to session for extra security
        "user_agent": request.headers.get('user-agent'),
        "remote_addr": (request.client.host if request.client else None),
    }
    await db.sessions.insert_one(session_doc)

    try:
        token = encrypt_value(session_id, require_key=True)
    except RuntimeError:
        # Encryption key missing; fail safe.
        return RedirectResponse(url='/login', status_code=303)

    # Cookie security settings - use strict SameSite and secure in production.
    cookie_name = os.getenv("SESSION_COOKIE_NAME", "rental_session")
    cookie_secure = os.getenv("COOKIE_SECURE", "1") in ("1", "true", "True")
    cookie_samesite = os.getenv("COOKIE_SAMESITE", "strict")

    response = RedirectResponse(url='/dashboard', status_code=303)
    response.set_cookie(
        cookie_name,
        token,
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=8 * 3600,
        path='/',
    )
    return response


@router.get('/logout')
async def logout(request: Request):
    # Remove server-side session and clear cookie
    db = get_db()
    cookie_name = os.getenv("SESSION_COOKIE_NAME", "rental_session")
    session_cookie = request.cookies.get(cookie_name)
    if session_cookie:
        from security import decrypt_value

        try:
            session_id = decrypt_value(session_cookie)
        except Exception:
            session_id = None

        if session_id:
            await db.sessions.delete_one({"_id": session_id})

    response = RedirectResponse(url='/login')
    response.delete_cookie(cookie_name)
    return response
