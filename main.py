from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import os

from app.routers import rooms, tenants, contracts, bills, electric, dashboard, invoice, auth

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


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path or "/"
    public_prefixes = ("/login", "/logout", "/static", "/.well-known")
    if path.startswith(public_prefixes):
        return await call_next(request)

    auth_cookie = request.cookies.get("rental_auth")
    role_cookie = request.cookies.get("rental_role", "")
    if auth_cookie != "1":
        return RedirectResponse(url="/login", status_code=303)

    request.state.user_role = role_cookie or "guest"

    admin_only_prefixes = ("/rooms", "/tenants", "/contracts", "/electric", "/bills", "/invoice")
    if path.startswith(admin_only_prefixes) and request.state.user_role != "admin":
        if request.method != "GET":
            return JSONResponse({"detail": "Bạn không có quyền hạn để thấy"}, status_code=403)
        return RedirectResponse(
            url="/dashboard?flash=Bạn%20không%20có%20quyền%20hạn%20để%20thấy&level=warning",
            status_code=303,
        )

    return await call_next(request)


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_probe():
    # Chrome DevTools makes this request automatically in some environments.
    return JSONResponse(content={})
