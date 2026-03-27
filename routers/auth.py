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
    # simple auth from env
    u = os.getenv('ADMIN_USER', 'admin')
    p = os.getenv('ADMIN_PASS', 'password')
    if username == u and password == p:
        response = RedirectResponse(url='/dashboard', status_code=303)
        response.set_cookie('rental_admin', '1')
        return response
    return RedirectResponse(url='/login', status_code=303)


@router.get('/logout')
async def logout():
    response = RedirectResponse(url='/login')
    response.delete_cookie('rental_admin')
    return response
