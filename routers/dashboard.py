from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import os
from jinja2 import Environment, FileSystemLoader
from deps import get_db

from template_filters import money

router = APIRouter(tags=["dashboard"]) 

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.filters["money"] = money


@router.get("/dashboard")
async def dashboard_view(request: Request):
    role = getattr(request.state, "user_role", "guest")

    db = get_db()
    total_rooms = await db.rooms.count_documents({})
    occupied = await db.rooms.count_documents({"status": "occupied"})
    available = await db.rooms.count_documents({"status": "available"})
    paid = await db.bills.count_documents({"status": "paid"})
    unpaid = await db.bills.count_documents({"status": "unpaid"})
    # monthly revenue: compute totals for last 6 months
    import datetime
    now = datetime.datetime.now()
    labels = []
    series = []
    for i in range(5, -1, -1):
        m = (now.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        # shift back i months from current month
        target = (now.replace(day=1) - datetime.timedelta(days=1))
        target = now - datetime.timedelta(days=now.day-1)  # first of month
        # compute month label
        target_month = (now - datetime.timedelta(days=30*i)).strftime("%Y-%m")
        labels.append(target_month)
        cursor = db.bills.find({"status": "paid", "month": target_month})
        total_m = 0
        async for b in cursor:
            total_m += int(b.get("total", 0))
        series.append(total_m)

    # total revenue for current month
    revenue = series[-1] if series else 0

    # tenant rental status
    renting_tenants = await db.tenants.count_documents({"rental_status": "Đang thuê"})
    ended_tenants = await db.tenants.count_documents({"rental_status": "Đã kết thúc"})

    # top rooms by electric usage (all-time)
    room_usage = {}
    room_numbers = {}
    async for room in db.rooms.find({}):
        room_numbers[str(room.get("_id"))] = str(room.get("room_number"))
    async for r in db.electric_readings.find({}):
        rid = str(r.get("room_id") or "")
        try:
            usage = int(r.get("usage", 0))
        except Exception:
            usage = 0
        if not rid:
            continue
        room_usage[rid] = room_usage.get(rid, 0) + usage
    items = sorted(room_usage.items(), key=lambda kv: kv[1], reverse=True)[:5]
    top_room_labels = []
    top_room_usage = []
    for rid, usage in items:
        label = room_numbers.get(rid, rid)
        top_room_labels.append(f"Phòng {label}")
        top_room_usage.append(usage)

    # total electricity usage (all-time and current month)
    total_electric_all = 0
    total_electric_month = 0
    current_month = now.strftime('%Y-%m')
    async for r in db.electric_readings.find({}):
        try:
            usage = int(r.get('usage', 0))
        except Exception:
            usage = 0
        total_electric_all += usage
        if (r.get('month') or '') == current_month:
            total_electric_month += usage

    # total accounts
    total_accounts = await db.accounts.count_documents({})

    tpl = env.get_template("dashboard.html")
    html = tpl.render(
        request=request,
        total_rooms=total_rooms,
        occupied=occupied,
        available=available,
        paid=paid,
        unpaid=unpaid,
        revenue=revenue,
        revenue_labels=labels,
        revenue_series=series,
        renting_tenants=renting_tenants,
        ended_tenants=ended_tenants,
        top_room_labels=top_room_labels,
        top_room_usage=top_room_usage,
        total_electric_all=total_electric_all,
        total_electric_month=total_electric_month,
        total_accounts=total_accounts,
        readonly_guest=False,
    )
    return HTMLResponse(content=html)
