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
    from collections import defaultdict
    now = _dt.datetime.now()

    # 1. THỐNG KÊ CƠ BẢN (Nhanh)
    total_rooms = await db.rooms.count_documents({})
    occupied = await db.rooms.count_documents({"status": "occupied"})
    available = await db.rooms.count_documents({"status": "available"})
    paid = await db.bills.count_documents({"status": "paid"})
    unpaid = await db.bills.count_documents({"status": "unpaid"})
    renting_tenants = await db.tenants.count_documents({"rental_status": "Đang thuê"})
    ended_tenants = await db.tenants.count_documents({"rental_status": "Đã kết thúc"})
    total_accounts = await db.accounts.count_documents({})

    # helpers
    def month_label(year, month): return f"{year}-{month:02d}"
    def months_ago(start_dt, months_back):
        out = []
        y, m = start_dt.year, start_dt.month
        for i in range(months_back - 1, -1, -1):
            mm, yy = m - i, y
            while mm <= 0: mm += 12; yy -= 1
            out.append(month_label(yy, mm))
        return out

    # Chuẩn bị trước các mốc thời gian
    labels_6 = months_ago(now, 6)
    labels_12 = months_ago(now, 12)
    current_month_str = now.strftime('%Y-%m')
    
    electric_labels_30 = []
    tenant_labels_30 = []
    labels_30 = []
    days_30_objs = []
    for d in range(29, -1, -1):
        day = (now - _dt.timedelta(days=d)).date()
        days_30_objs.append(day)
        day_str = day.strftime('%d-%m')
        electric_labels_30.append(day_str)
        tenant_labels_30.append(day_str)
        labels_30.append(day_str)

    # ---------------------------------------------------------
    # BƯỚC 1: LOAD DỮ LIỆU TỪ DB (Chỉ lấy field cần thiết - PROJECTION)
    # ---------------------------------------------------------
    
    # A. Rooms
    room_dict = {} # room_id -> {"number": "", "price": 0}
    room_prices = []
    async for r in db.rooms.find({}, {"room_number": 1, "price": 1}):
        rid = str(r.get("_id"))
        p = int(r.get("price") or 0)
        room_dict[rid] = {"number": r.get("room_number", rid), "price": p}
        room_prices.append(p)
    
    room_price_avg = int(sum(room_prices) / len(room_prices)) if room_prices else 0

    # B. Payments (Gom nhóm theo bill_id và ngày/tháng)
    payment_by_bill = defaultdict(int)
    payment_by_month = defaultdict(int)
    payment_by_day = defaultdict(int)
    earliest_date = now.date()

    async for p in db.payments.find({}, {"bill_id": 1, "amount": 1, "payment_date": 1}):
        amt = int(p.get("amount") or 0)
        bid = str(p.get("bill_id") or "")
        p_date = p.get("payment_date")
        
        if bid: payment_by_bill[bid] += amt
        
        if p_date:
            if isinstance(p_date, str):
                try: p_date = _dt.datetime.fromisoformat(p_date.replace("Z", "+00:00")).date()
                except: p_date = None
            elif isinstance(p_date, _dt.datetime): p_date = p_date.date()
            
            if p_date:
                earliest_date = min(earliest_date, p_date)
                p_month_str = month_label(p_date.year, p_date.month)
                payment_by_month[p_month_str] += amt
                payment_by_day[p_date] += amt

    # C. Bills (Gom nhóm theo tháng)
    paid_bills_by_month = defaultdict(int)
    revenue_by_month = defaultdict(int)
    
    async for b in db.bills.find({}, {"month": 1, "total": 1, "status": 1, "paid_amount": 1}):
        b_month = b.get("month")
        if not b_month: continue
        
        try:
            d = _dt.date.fromisoformat(f"{b_month}-01")
            earliest_date = min(earliest_date, d)
        except: pass

        if b.get("status") == "paid":
            paid_bills_by_month[b_month] += int(b.get("total") or 0)
            
        paid_amt = int(b.get('paid_amount') or 0)
        if paid_amt == 0:
            # Fallback sang bảng payment nếu bill chưa cập nhật paid_amount
            paid_amt = payment_by_bill.get(str(b.get("_id")), 0)
            
        revenue_by_month[b_month] += paid_amt

    # D. Electric Readings
    electric_by_month = defaultdict(int)
    electric_by_day = defaultdict(int)
    electric_by_room = defaultdict(int)
    
    async for e in db.electric_readings.find({}, {"month": 1, "usage": 1, "room_id": 1}):
        e_month = str(e.get("month") or "")
        u = int(e.get("usage") or 0)
        rid = str(e.get("room_id") or "")
        
        if e_month:
            electric_by_month[e_month] += u
            try:
                d = _dt.date.fromisoformat(f"{e_month}-01")
                earliest_date = min(earliest_date, d)
            except: pass
            
        if rid:
            electric_by_room[rid] += u
            
        # Ước lượng ngày (Do record của bạn lưu theo tháng, phần này giữ logic best-effort của bạn)
        # Nếu muốn chính xác phải có create_at
        if len(e_month) >= 10: # Nếu là ISO format có ngày
            try:
                e_date = _dt.date.fromisoformat(e_month[:10])
                electric_by_day[e_date] += u
            except: pass

    # E. Contracts (Chỉ parse date, không kéo toàn bộ object)
    tenant_starts = defaultdict(int)
    tenant_ends = defaultdict(int)
    tenant_starts_day = defaultdict(int)
    tenant_ends_day = defaultdict(int)

    def parse_dt(val):
        if not val: return None
        if isinstance(val, _dt.datetime): return val.date()
        if isinstance(val, _dt.date): return val
        if isinstance(val, str):
            try: return _dt.date.fromisoformat(val[:10])
            except: return None
        return None

    async for c in db.contracts.find({}, {"start_date": 1, "termination_date": 1}):
        sd = parse_dt(c.get("start_date"))
        td = parse_dt(c.get("termination_date"))
        
        if sd:
            earliest_date = min(earliest_date, sd)
            m_str = month_label(sd.year, sd.month)
            tenant_starts[m_str] += 1
            tenant_starts_day[sd] += 1
        if td:
            earliest_date = min(earliest_date, td)
            m_str = month_label(td.year, td.month)
            tenant_ends[m_str] += 1
            tenant_ends_day[td] += 1

    # ---------------------------------------------------------
    # BƯỚC 2: RÁP DỮ LIỆU VÀO MẢNG CHART (Tra cứu Dictionary O(1))
    # ---------------------------------------------------------
    
    # Hàm helper map array
    def map_series_month(labels, data_dict): return [data_dict.get(lbl, 0) for lbl in labels]
    def map_series_day(days, data_dict): return [data_dict.get(d, 0) for d in days]

    # Series 6 Months & 12 Months
    payments_series_6 = map_series_month(labels_6, revenue_by_month)
    payments_series_12 = map_series_month(labels_12, revenue_by_month)
    
    electric_series_6 = map_series_month(labels_6, electric_by_month)
    electric_series_12 = map_series_month(labels_12, electric_by_month)
    
    tenant_started_6 = map_series_month(labels_6, tenant_starts)
    tenant_ended_6 = map_series_month(labels_6, tenant_ends)
    tenant_started_12 = map_series_month(labels_12, tenant_starts)
    tenant_ended_12 = map_series_month(labels_12, tenant_ends)

    # Series 30 Days
    payments_30 = map_series_day(days_30_objs, payment_by_day)
    electric_series_30 = map_series_day(days_30_objs, electric_by_day)
    tenant_started_30 = map_series_day(days_30_objs, tenant_starts_day)
    tenant_ended_30 = map_series_day(days_30_objs, tenant_ends_day)

    # Series All Time (Tính toán danh sách tháng từ earliest_date đến now)
    labels_all = []
    sy, sm = earliest_date.year, earliest_date.month
    ey, em = now.year, now.month
    while (sy < ey) or (sy == ey and sm <= em):
        labels_all.append(month_label(sy, sm))
        if sm == 12: sy += 1; sm = 1
        else: sm += 1

    payments_all = map_series_month(labels_all, revenue_by_month)
    electric_series_all = map_series_month(labels_all, electric_by_month)
    tenant_started_all = map_series_month(labels_all, tenant_starts)
    tenant_ended_all = map_series_month(labels_all, tenant_ends)

    # Top Electric Rooms (All time)
    top_rooms = sorted(electric_by_room.items(), key=lambda x: x[1], reverse=True)[:5]
    top_room_labels = [f"Phòng {room_dict.get(rid, {}).get('number', rid)}" for rid, _ in top_rooms]
    top_room_usage = [usage for _, usage in top_rooms]

    # Current month variables
    paid_amount_current_month = revenue_by_month.get(current_month_str, 0)

    # Constants
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
        
        "labels6": labels_6,
        "payments6": payments_series_6,
        "labels12": labels_12,
        "payments12": payments_series_12,
        "labels30": labels_30,
        "payments30": payments_30,
        "labels_all": labels_all,
        "payments_all": payments_all,
        
        "electric_labels_6": labels_6, # Reusing labels
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
