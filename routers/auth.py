from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import RedirectResponse
import os

router = APIRouter()


@router.get('/login')
async def login_get(request: Request):
    from fastapi.templating import Jinja2Templates
    import os as _os
    templates = Jinja2Templates(directory=_os.path.join(_os.path.dirname(__file__), '..', 'templates'))
    return templates.TemplateResponse('login.html', {'request': request})


@router.post('/login')
async def login_post(response: Response, username: str = Form(...), password: str = Form(...)):
    # Role-based auth from env
    admin_user = os.getenv('ADMIN_USER', 'admin')
    admin_pass = os.getenv('ADMIN_PASS', 'password')
    guest_user = os.getenv('GUEST_USER', 'guest')
    guest_pass = os.getenv('GUEST_PASS', 'guest')

    role = None
    if username == admin_user and password == admin_pass:
        role = "admin"
    elif username == guest_user and password == guest_pass:
        role = "guest"

    if role:
        response = RedirectResponse(url='/dashboard', status_code=303)
        response.set_cookie('rental_auth', '1', httponly=True, samesite='lax')
        response.set_cookie('rental_role', role, httponly=True, samesite='lax')
        return response
    return RedirectResponse(url='/login', status_code=303)


@router.get('/logout')
async def logout():
    response = RedirectResponse(url='/login')
    response.delete_cookie('rental_auth')
    response.delete_cookie('rental_role')
    return response
