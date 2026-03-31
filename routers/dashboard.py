from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import os
from jinja2 import Environment, FileSystemLoader
from core.deps import get_db
from core.template_filters import money
from core import constants

router = APIRouter(tags=["dashboard"]) 

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.filters["money"] = money

# 1. API Trả về khung HTML (Load ngay lập tức)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    tpl = env.get_template("dashboard.html")
    # Chỉ truyền role để check quyền ẩn/hiện menu, không truyền data
    html = tpl.render(request=request)
    return HTMLResponse(content=html)

# 2. API Trả về JSON Dữ liệu (Sẽ được gọi ngầm qua Javascript)
@router.get("/dashboard/_data")
async def dashboard_data_api():
    db = get_db()
    import datetime as _dt
    now = _dt.datetime.now()
    
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

        # sum actual paid amounts on bills for this month (fallback to payments collection for legacy records)
        pay_total = 0
        bcur = db.bills.find({"month": target})
        async for b in bcur:
            try:
                paid_amt = int(b.get('paid_amount', 0) or 0)
            except Exception:
                paid_amt = 0
            if paid_amt:
                pay_total += paid_amt
            else:
                # fallback to payments collection entries for this bill
                try:
                    bid = str(b.get('_id'))
                    pc = db.payments.find({"bill_id": bid})
                    async for p in pc:
                        try:
                            pay_total += int(p.get('amount', 0) or 0)
                        except Exception:
                            pass
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

    # electric consumption for 12 months
    electric_series_12 = []
    for yy, mm in months_ago(now, 12):
        target = month_label(yy, mm)
        e_total = 0
        ecursor = db.electric_readings.find({"month": target})
        async for er in ecursor:
            try:
                e_total += int(er.get('usage', 0) or 0)
            except Exception:
                pass
        electric_series_12.append(e_total)

    # electric consumption for last 30 days (per day)
    electric_labels_30 = []
    electric_series_30 = []
    for d in range(29, -1, -1):
        day = (now - _dt.timedelta(days=d)).date()
        electric_labels_30.append(day.strftime('%d-%m'))
        day_iso = day.isoformat()
        # sum readings whose month or date matches the day (best-effort)
        e_total = 0
        # try to find readings with exact day in month field or separate stored date
        ecursor = db.electric_readings.find({"month": {"$regex": f'^{day_iso[:7]}'}})
        async for er in ecursor:
            try:
                e_total += int(er.get('usage', 0) or 0)
            except Exception:
                pass
        electric_series_30.append(e_total)

    # tenant churn/start series (new contracts and contract ends) for same ranges
    # Contracts may store dates as strings (ISO) or as date/datetime objects.
    # We will load contracts once and compute counts robustly. For 'ended' we
    # only count explicit 'termination_date' values (user-requested behavior).
    contracts_list = []
    async for c in db.contracts.find({}):
        contracts_list.append(c)

    def _parse_to_date(val):
        if not val:
            return None
        try:
            # date string YYYY-MM-DD or ISO
            import datetime as _dt
            if isinstance(val, str):
                try:
                    return _dt.date.fromisoformat(val)
                except Exception:
                    try:
                        dt = _dt.datetime.fromisoformat(val)
                        return dt.date()
                    except Exception:
                        return None
            # datetime.date or datetime.datetime
            try:
                if hasattr(val, 'date') and not isinstance(val, str):
                    # datetime -> date
                    if isinstance(val, _dt.datetime):
                        return val.date()
                    if isinstance(val, _dt.date):
                        return val
            except Exception:
                return None
        except Exception:
            return None
        return None

    # helper to count dates in a target month (YYYY-MM)
    def _count_in_month(dt_list, year, month):
        c = 0
        for d in dt_list:
            if not d:
                continue
            if d.year == year and d.month == month:
                c += 1
        return c

    # precompute lists of start_date and termination_date as date objects
    start_dates = []
    termination_dates = []
    for c in contracts_list:
        sd = _parse_to_date(c.get('start_date'))
        td = _parse_to_date(c.get('termination_date'))
        start_dates.append(sd)
        termination_dates.append(td)

    tenant_started_6 = []
    tenant_ended_6 = []
    for yy, mm in months_ago(now, 6):
        tenant_started_6.append(_count_in_month(start_dates, yy, mm))
        tenant_ended_6.append(_count_in_month(termination_dates, yy, mm))

    tenant_started_12 = []
    tenant_ended_12 = []
    for yy, mm in months_ago(now, 12):
        tenant_started_12.append(_count_in_month(start_dates, yy, mm))
        tenant_ended_12.append(_count_in_month(termination_dates, yy, mm))

    # last 30 days tenant starts/ends (per day)
    tenant_labels_30 = []
    tenant_started_30 = []
    tenant_ended_30 = []
    for d in range(29, -1, -1):
        day = (now - _dt.timedelta(days=d)).date()
        tenant_labels_30.append(day.strftime('%d-%m'))
        # count exact day matches
        s = sum(1 for dt in start_dates if dt == day)
        e = sum(1 for dt in termination_dates if dt == day)
        tenant_started_30.append(s)
        tenant_ended_30.append(e)

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

        # sum actual paid amounts on bills for this month (fallback to payments collection for legacy records)
        pay_total = 0
        bcur = db.bills.find({"month": target})
        async for b in bcur:
            try:
                paid_amt = int(b.get('paid_amount', 0) or 0)
            except Exception:
                paid_amt = 0
            if paid_amt:
                pay_total += paid_amt
            else:
                try:
                    bid = str(b.get('_id'))
                    pc = db.payments.find({"bill_id": bid})
                    async for p in pc:
                        try:
                            pay_total += int(p.get('amount', 0) or 0)
                        except Exception:
                            pass
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

    # --- All-time monthly series (from earliest recorded month to now)
    labels_all = []
    payments_all = []
    electric_series_all = []
    tenant_started_all = []
    tenant_ended_all = []
    try:
        # find earliest dates across collections (best-effort)
        earliest = now.date()
        # payments
        try:
            pdoc = await db.payments.find_one({}, sort=[("payment_date", 1)])
            if pdoc and pdoc.get('payment_date'):
                pd = pdoc.get('payment_date')
                if isinstance(pd, _dt.datetime):
                    earliest = min(earliest, pd.date())
                else:
                    try:
                        earliest = min(earliest, _dt.date.fromisoformat(str(pd)))
                    except Exception:
                        pass
        except Exception:
            pass
        # bills (month string YYYY-MM)
        try:
            bdoc = await db.bills.find_one({}, sort=[("month", 1)])
            if bdoc and bdoc.get('month'):
                try:
                    d = _dt.date.fromisoformat(str(bdoc.get('month')) + '-01')
                    earliest = min(earliest, d)
                except Exception:
                    pass
        except Exception:
            pass
        # electric_readings (month)
        try:
            edoc = await db.electric_readings.find_one({}, sort=[("month", 1)])
            if edoc and edoc.get('month'):
                try:
                    d = _dt.date.fromisoformat(str(edoc.get('month')) + '-01')
                    earliest = min(earliest, d)
                except Exception:
                    pass
        except Exception:
            pass
        # contracts start_date
        try:
            cdoc = await db.contracts.find_one({}, sort=[("start_date", 1)])
            if cdoc and cdoc.get('start_date'):
                try:
                    dval = cdoc.get('start_date')
                    if isinstance(dval, str):
                        d = _dt.date.fromisoformat(dval)
                    elif isinstance(dval, _dt.datetime):
                        d = dval.date()
                    elif isinstance(dval, _dt.date):
                        d = dval
                    else:
                        d = None
                    if d:
                        earliest = min(earliest, d)
                except Exception:
                    pass
        except Exception:
            pass

        # build month range from earliest.year-month to now.year-month
        sy, sm = earliest.year, earliest.month
        ey, em = now.year, now.month
        cur_y, cur_m = sy, sm
        months = []
        while (cur_y < ey) or (cur_y == ey and cur_m <= em):
            months.append((cur_y, cur_m))
            if cur_m == 12:
                cur_y += 1; cur_m = 1
            else:
                cur_m += 1

        for yy, mm in months:
            label = f"{yy}-{mm:02d}"
            labels_all.append(label)
            # payments in month
            start_dt = _dt.datetime(yy, mm, 1)
            if mm == 12:
                next_dt = _dt.datetime(yy + 1, 1, 1)
            else:
                next_dt = _dt.datetime(yy, mm + 1, 1)
            
            pay_total = 0
            try:
                bcur = db.bills.find({"month": label})
                async for b in bcur:
                    try:
                        paid_amt = int(b.get('paid_amount', 0) or 0)
                    except Exception:
                        paid_amt = 0
                    if paid_amt:
                        pay_total += paid_amt
                    else:
                        try:
                            bid = str(b.get('_id'))
                            pc = db.payments.find({"bill_id": bid})
                            async for p in pc:
                                try:
                                    pay_total += int(p.get('amount', 0) or 0)
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except Exception:
                pay_total = 0
            payments_all.append(pay_total)

            # electric usage in month
            e_total = 0
            try:
                ec = db.electric_readings.find({"month": label})
                async for er in ec:
                    try:
                        e_total += int(er.get('usage', 0) or 0)
                    except Exception:
                        pass
            except Exception:
                e_total = 0
            electric_series_all.append(e_total)

            # tenant starts/ends in month using precomputed start_dates/termination_dates
            try:
                s = _count_in_month(start_dates, yy, mm)
                e = _count_in_month(termination_dates, yy, mm)
            except Exception:
                s = 0; e = 0
            tenant_started_all.append(s)
            tenant_ended_all.append(e)
    except Exception:
        labels_all = []
        payments_all = []
        electric_series_all = []
        tenant_started_all = []
        tenant_ended_all = []

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
        # compute paid amount for current month by summing paid_amount on bills (fallback to payments collection)
        s = 0
        bcur = db.bills.find({"month": current_month})
        async for b in bcur:
            try:
                paid_amt = int(b.get('paid_amount', 0) or 0)
            except Exception:
                paid_amt = 0
            if paid_amt:
                s += paid_amt
            else:
                try:
                    bid = str(b.get('_id'))
                    pc = db.payments.find({"bill_id": bid})
                    async for p in pc:
                        try:
                            s += int(p.get('amount', 0) or 0)
                        except Exception:
                            pass
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

    return {
        "total_rooms": total_rooms,
        "occupied": occupied,
        "available": available,
        "paid": paid,
        "unpaid": unpaid,
        "paid_amount_current_month": paid_amount_current_month,
        "room_price_avg": room_price_avg,
        "price_per_kwh": price_per_kwh,
        "water_fee": water_fee,
        "total_accounts": total_accounts,
        
        # Dữ liệu cho Chart.js
        "labels6": labels_6,
        "payments6": payments_series_6,
        "labels12": labels_12,
        "payments12": payments_series_12,
        "labels30": labels_30,
        "payments30": payments_30,
        "labels_all": labels_all,
        "payments_all": payments_all,
        
        "electric_labels_6": labels_6,
        "electric_series_6": electric_series_6,
        "electric_labels_12": labels_12,
        "electric_series_12": electric_series_12,
        "electric_labels_30": electric_labels_30,
        "electric_series_30": electric_series_30,
        "electric_labels_all": labels_all,
        "electric_series_all": electric_series_all,
        
        "tenant_started_6": tenant_started_6,
        "tenant_ended_6": tenant_ended_6,
        "tenant_started_12": tenant_started_12,
        "tenant_ended_12": tenant_ended_12,
        "tenant_labels_30": tenant_labels_30,
        "tenant_started_30": tenant_started_30,
        "tenant_ended_30": tenant_ended_30,
        "tenant_started_all": tenant_started_all,
        "tenant_ended_all": tenant_ended_all,
        
        "top_room_labels": top_room_labels,
        "top_room_usage": top_room_usage,
        "renting_tenants": renting_tenants,
        "ended_tenants": ended_tenants
    }


@router.get('/dashboard/top-electric/{month}')
async def top_electric_by_month(month: str):
    """Return top rooms by electric usage for a given month."""
    db = get_db()
    # aggregate usage per room_id for the requested month
    usage_map = {}
    async for r in db.electric_readings.find({"month": month}):
        try:
            rid = str(r.get('room_id') or '')
            u = int(r.get('usage', 0) or 0)
        except Exception:
            continue
        if not rid:
            continue
        usage_map[rid] = usage_map.get(rid, 0) + u

    # resolve room numbers
    room_numbers = {}
    async for room in db.rooms.find({}):
        room_numbers[str(room.get('_id'))] = room.get('room_number')

    items = sorted(usage_map.items(), key=lambda kv: kv[1], reverse=True)[:10]
    out = []
    for rid, usage in items:
        label = room_numbers.get(rid, rid)
        out.append({"room_id": rid, "room_number": label, "usage": usage})
    return {"month": month, "top_rooms": out}


@router.get('/dashboard/top-electric-year/{year}')
async def top_electric_by_year(year: str):
    """Return monthly totals for a given year, sorted desc (top months)."""
    db = get_db()
    # collect usage per month in the year
    month_map = {}
    prefix = f"{year}-"
    async for r in db.electric_readings.find({"month": {"$regex": f'^{prefix}'}}):
        try:
            m = str(r.get('month') or '')
            u = int(r.get('usage', 0) or 0)
        except Exception:
            continue
        if not m:
            continue
        month_map[m] = month_map.get(m, 0) + u

    items = sorted(month_map.items(), key=lambda kv: kv[1], reverse=True)
    out = []
    for m, usage in items:
        out.append({"month": m, "usage": usage})
    return {"year": year, "top_months": out}


# Backwards-compatible legacy routes (some clients may still call /electric/dashboard/...)
@router.get('/electric/dashboard/top-electric/{month}')
async def legacy_top_electric_by_month(month: str):
    return await top_electric_by_month(month)


@router.get('/electric/dashboard/top-electric-year/{year}')
async def legacy_top_electric_by_year(year: str):
    return await top_electric_by_year(year)
