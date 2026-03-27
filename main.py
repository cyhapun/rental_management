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


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_probe():
    # Chrome DevTools makes this request automatically in some environments.
    return JSONResponse(content={})
