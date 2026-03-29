from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import os
from jinja2 import Environment, FileSystemLoader
from deps import get_db

from template_filters import money
import constants

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

    import datetime as _dt
    now = _dt.datetime.now()

    # helpers for month series
    def month_label(year, month):
        return f"{year}-{month:02d}"

    def months_ago(start_dt, months_back):
        y = start_dt.year
        m = start_dt.month
        out = []
        for i in range(months_back - 1, -1, -1):
            mm = m - i
            yy = y
            while mm <= 0:
                mm += 12
                yy -= 1
            out.append((yy, mm))
        return out

    # 6-month and 12-month series
    labels_6 = []
    paid_series_6 = []
    payments_series_6 = []
    labels_12 = []
    paid_series_12 = []
    payments_series_12 = []

    for yy, mm in months_ago(now, 6):
        target = month_label(yy, mm)
        labels_6.append(target)
        total_m = 0
        cursor = db.bills.find({"status": "paid", "month": target})
        async for b in cursor:
            try:
                total_m += int(b.get("total", 0) or 0)
            except Exception:
                pass
        paid_series_6.append(total_m)

        first_day = _dt.datetime(yy, mm, 1)
        if mm == 12:
            next_day = _dt.datetime(yy + 1, 1, 1)
        else:
            next_day = _dt.datetime(yy, mm + 1, 1)
        pay_total = 0
        pcursor = db.payments.find({"payment_date": {"$gte": first_day, "$lt": next_day}})
        async for p in pcursor:
            try:
                pay_total += int(p.get("amount", 0) or 0)
            except Exception:
                pass
        payments_series_6.append(pay_total)

    # electric consumption series for last 6 months
    electric_series_6 = []
    for yy, mm in months_ago(now, 6):
        target = month_label(yy, mm)
        e_total = 0
        ecursor = db.electric_readings.find({"month": target})
        async for er in ecursor:
            try:
                e_total += int(er.get('usage', 0) or 0)
            except Exception:
                pass
        electric_series_6.append(e_total)

    for yy, mm in months_ago(now, 12):
        target = month_label(yy, mm)
        labels_12.append(target)
        total_m = 0
        cursor = db.bills.find({"status": "paid", "month": target})
        async for b in cursor:
            try:
                total_m += int(b.get("total", 0) or 0)
            except Exception:
                pass
        paid_series_12.append(total_m)

        first_day = _dt.datetime(yy, mm, 1)
        if mm == 12:
            next_day = _dt.datetime(yy + 1, 1, 1)
        else:
            next_day = _dt.datetime(yy, mm + 1, 1)
        pay_total = 0
        pcursor = db.payments.find({"payment_date": {"$gte": first_day, "$lt": next_day}})
        async for p in pcursor:
            try:
                pay_total += int(p.get("amount", 0) or 0)
            except Exception:
                pass
        payments_series_12.append(pay_total)

    # last 30 days payments
    labels_30 = []
    payments_30 = []
    for d in range(29, -1, -1):
        day = (now - _dt.timedelta(days=d)).date()
        labels_30.append(day.strftime('%d-%m'))
        start_dt = _dt.datetime(day.year, day.month, day.day, 0, 0, 0)
        end_dt = start_dt + _dt.timedelta(days=1)
        pay_total = 0
        pcursor = db.payments.find({"payment_date": {"$gte": start_dt, "$lt": end_dt}})
        async for p in pcursor:
            try:
                pay_total += int(p.get("amount", 0) or 0)
            except Exception:
                pass
        payments_30.append(pay_total)

    # default 6-month variables for backward compatibility
    labels = labels_6
    series = paid_series_6
    payments_series = payments_series_6

    # billed total and paid amount current month
    current_month = now.strftime('%Y-%m')
    billed_total_current_month = 0
    try:
        cursor_all = db.bills.find({"month": current_month})
        async for b in cursor_all:
            try:
                billed_total_current_month += int(b.get('total', 0) or 0)
            except Exception:
                pass
    except Exception:
        billed_total_current_month = 0

    paid_amount_current_month = 0
    try:
        if current_month in labels_6:
            paid_amount_current_month = payments_series_6[labels_6.index(current_month)]
        else:
            ty = now.year; tm = now.month
            first_day = _dt.datetime(ty, tm, 1)
            if tm == 12:
                next_day = _dt.datetime(ty + 1, 1, 1)
            else:
                next_day = _dt.datetime(ty, tm + 1, 1)
            pcur = db.payments.find({"payment_date": {"$gte": first_day, "$lt": next_day}})
            s = 0
            async for p in pcur:
                try:
                    s += int(p.get('amount', 0) or 0)
                except Exception:
                    pass
            paid_amount_current_month = s
    except Exception:
        paid_amount_current_month = 0

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

    # room price statistics
    room_prices = []
    async for r in db.rooms.find({}):
        try:
            p = int(r.get('price') or 0)
        except Exception:
            p = 0
        room_prices.append(p)
    room_price_avg = int(sum(room_prices) / len(room_prices)) if room_prices else 0
    room_price_min = min(room_prices) if room_prices else 0
    room_price_max = max(room_prices) if room_prices else 0

    # currency / utility constants
    price_per_kwh = getattr(constants, 'PRICE_PER_KWH', 3000)
    water_fee = getattr(constants, 'WATER_FEE', 50000)

    tpl = env.get_template("dashboard.html")
    html = tpl.render(
        request=request,
        total_rooms=total_rooms,
        occupied=occupied,
        available=available,
        paid=paid,
        unpaid=unpaid,
        revenue=series[-1] if series else 0,
        revenue_labels=labels,
        revenue_series=series,
        billed_total_current_month=billed_total_current_month,
        payments_series=payments_series,
        paid_amount_current_month=paid_amount_current_month,
        labels_12=labels_12,
        payments_series_12=payments_series_12,
        labels_30=labels_30,
        payments_30=payments_30,
        renting_tenants=renting_tenants,
        ended_tenants=ended_tenants,
        top_room_labels=top_room_labels,
        top_room_usage=top_room_usage,
        total_electric_all=total_electric_all,
        total_electric_month=total_electric_month,
        total_accounts=total_accounts,
        room_price_avg=room_price_avg,
        room_price_min=room_price_min,
        room_price_max=room_price_max,
        price_per_kwh=price_per_kwh,
        water_fee=water_fee,
        electric_labels_6=labels_6,
        electric_series_6=electric_series_6,
        readonly_guest=False,
    )
    return HTMLResponse(content=html)
