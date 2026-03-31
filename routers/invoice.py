
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from core.deps import get_db
import os
from jinja2 import Environment, FileSystemLoader
import io
import datetime

from core.security import decrypt_value
from core.template_filters import money
from core.constants import WATER_FEE
from bson import ObjectId

router = APIRouter(prefix="/invoice", tags=["invoice"])


def render_template(name: str, context: dict):
    base = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(base))
    env.filters["money"] = money
    tpl = env.get_template(name)
    return tpl.render(**context)


@router.get("/print/{bill_id}", response_class=HTMLResponse)
async def print_invoice(bill_id: str, request: Request):
    db = get_db()
    bill = await db.bills.find_one({"_id": bill_id})
    # bill._id might be ObjectId depending on how stored
    if not bill:
        # try ObjectId
        try:
            bill = await db.bills.find_one({"_id": ObjectId(bill_id)})
        except Exception:
            bill = None
    # If still not found, the provided id may be a contract/room/tenant id.
    if not bill:
        try:
            # try direct match on contract_id stored on bills
            bill = await db.bills.find_one({"contract_id": bill_id}, sort=[("month", -1)])
            if not bill:
                bill = await db.bills.find_one({"contract_id": str(bill_id)}, sort=[("month", -1)])
            # try to locate contract by id and then find its latest bill
            if not bill:
                contract = await db.contracts.find_one({"_id": bill_id}) or await db.contracts.find_one({"_id": ObjectId(bill_id)}) or await db.contracts.find_one({"_id": str(bill_id)})
                if contract:
                    cid = str(contract.get("_id"))
                    bill = await db.bills.find_one({"contract_id": cid}, sort=[("month", -1)])
            # try to find contracts by room_id or tenant_id, then lookup bills
            if not bill:
                contracts_cursor = db.contracts.find({"$or": [{"room_id": bill_id}, {"room_id": str(bill_id)}, {"tenant_id": bill_id}, {"tenant_id": str(bill_id)}]})
                async for c in contracts_cursor:
                    cid = str(c.get("_id"))
                    candidate = await db.bills.find_one({"contract_id": cid}, sort=[("month", -1)])
                    if candidate:
                        bill = candidate
                        break
        except Exception:
            pass
    if not bill:
        raise HTTPException(404, "Bill not found")
    # fetch contract, tenant, room with robust ID handling
    tenant = None
    room = None
    contract = None

    async def _resolve_document(collection, doc_id):
        """Try to resolve a document by various id formats."""
        if not doc_id:
            return None
        # try direct
        try:
            d = await collection.find_one({"_id": doc_id})
            if d:
                return d
        except Exception:
            pass
        # try as ObjectId
        try:
            d = await collection.find_one({"_id": ObjectId(doc_id)})
            if d:
                return d
        except Exception:
            pass
        # try string form
        try:
            d = await collection.find_one({"_id": str(doc_id)})
            if d:
                return d
        except Exception:
            pass
        return None

    # resolve contract using the same robust method
    contract = await _resolve_document(db.contracts, bill.get("contract_id"))
    if contract:
        tenant = await _resolve_document(db.tenants, contract.get("tenant_id"))
        room = await _resolve_document(db.rooms, contract.get("room_id"))
        if tenant:
            try:
                tenant["phone"] = decrypt_value(tenant.get("phone"))
            except Exception:
                pass

    # attach contract display info into bill for template fallback
    try:
        bill['contract_display'] = {
            'tenant_name': tenant.get('full_name') if tenant else None,
            'room_number': room.get('room_number') if room else None,
        }
    except Exception:
        bill['contract_display'] = {'tenant_name': None, 'room_number': None}

    # expose a current electric index fallback from room document if available
    try:
        if room:
            ci = room.get('current_electric_index')
            if ci is None:
                # try to sync like electric._sync_room_current_index: find latest reading
                try:
                    r_oid = room.get('_id')
                    rnum = room.get('room_number')
                    latest = await db.electric_readings.find_one({"$or": [{"room_id": r_oid}, {"room_id": str(r_oid)}, {"room_id": rnum}, {"room_id": str(rnum)}]}, sort=[("month", -1)])
                except Exception:
                    latest = None
                if latest:
                    try:
                        ci = int(latest.get('new_index'))
                    except Exception:
                        ci = latest.get('new_index')
            if ci is not None:
                bill['room_current_electric_index'] = ci
            else:
                bill['room_current_electric_index'] = None
        else:
            bill['room_current_electric_index'] = None
    except Exception:
        bill['room_current_electric_index'] = None

    # Backfill legacy bills missing water_cost/total so invoice modal shows đúng.
    try:
        water_cost_val = bill.get("water_cost")
        if water_cost_val is None or int(water_cost_val) == 0:
            bill["water_cost"] = WATER_FEE
    except Exception:
        bill["water_cost"] = WATER_FEE
    try:
        room_price = int(bill.get("room_price", 0) or 0)
        electric_cost = int(bill.get("electric_cost", 0) or 0)
        water_cost = int(bill.get("water_cost", 0) or 0)
        other_cost = int(bill.get("other_cost", 0) or 0)
        bill["total"] = room_price + electric_cost + water_cost + other_cost
    except Exception:
        pass

    # If bill is missing electric indices/usage, try to find the electric reading for the room/month
    try:
        if (not bill.get('prev_index') or not bill.get('curr_index') or not bill.get('usage')) and room:
            month_val = bill.get('month')
            candidates = []
            r_id = room.get('_id')
            try:
                candidates.append(r_id)
            except Exception:
                pass
            try:
                candidates.append(str(r_id))
            except Exception:
                pass
            try:
                rn = room.get('room_number')
                if rn is not None:
                    candidates.append(rn)
                    candidates.append(str(rn))
            except Exception:
                pass
            try:
                cid = bill.get('contract_id')
                if cid:
                    candidates.append(cid)
                    candidates.append(str(cid))
            except Exception:
                pass

            reading = None
            try:
                or_clauses = []
                for c in candidates:
                    or_clauses.append({"room_id": c})
                if or_clauses:
                    reading = await db.electric_readings.find_one({"$and": [{"month": month_val}, {"$or": or_clauses}]})
            except Exception:
                reading = None

            if not reading:
                try:
                    if or_clauses:
                        reading = await db.electric_readings.find_one({"$or": or_clauses}, sort=[("month", -1)])
                except Exception:
                    reading = None

            if reading:
                bill['prev_index'] = bill.get('prev_index') or reading.get('old_index')
                bill['curr_index'] = bill.get('curr_index') or reading.get('new_index')
                bill['usage'] = bill.get('usage') or reading.get('usage')
                bill['kwh_price'] = bill.get('kwh_price') or reading.get('price_per_kwh')
                # update electric_cost if missing
                if not bill.get('electric_cost'):
                    bill['electric_cost'] = reading.get('total') or bill.get('electric_cost')
                # Also backfill bill in DB asynchronously when useful
                try:
                    await db.bills.update_one({"_id": bill.get('_id')}, {"$set": {"prev_index": bill.get('prev_index'), "curr_index": bill.get('curr_index'), "usage": bill.get('usage'), "kwh_price": bill.get('kwh_price'), "electric_cost": bill.get('electric_cost')}})
                except Exception:
                    pass
    except Exception:
        pass

    # Format created_at for display (d/m/Y) if present
    try:
        ca = bill.get('created_at')
        if isinstance(ca, datetime.datetime):
            bill['created_at_fmt'] = ca.strftime('%d/%m/%Y')
        else:
            try:
                bill['created_at_fmt'] = datetime.datetime.fromisoformat(str(ca)).strftime('%d/%m/%Y')
            except Exception:
                # fallback: if it's a timestamp number
                try:
                    bill['created_at_fmt'] = datetime.datetime.utcfromtimestamp(float(ca)).strftime('%d/%m/%Y')
                except Exception:
                    bill['created_at_fmt'] = str(ca)[:10] if ca else ''
    except Exception:
        bill['created_at_fmt'] = ''

    # Format paid_at for display if present
    try:
        pa = bill.get('paid_at')
        if pa:
            if isinstance(pa, datetime.datetime):
                bill['paid_at_fmt'] = pa.strftime('%d/%m/%Y %H:%M')
            else:
                try:
                    bill['paid_at_fmt'] = datetime.datetime.fromisoformat(str(pa)).strftime('%d/%m/%Y %H:%M')
                except Exception:
                    try:
                        bill['paid_at_fmt'] = datetime.datetime.utcfromtimestamp(float(pa)).strftime('%d/%m/%Y %H:%M')
                    except Exception:
                        bill['paid_at_fmt'] = str(pa)
        else:
            bill['paid_at_fmt'] = ''
    except Exception:
        bill['paid_at_fmt'] = ''

    html = render_template("invoice_print.html", {"bill": bill, "tenant": tenant, "room": room, "request": request})
    return HTMLResponse(content=html)


@router.get("/pdf/{bill_id}")
async def invoice_pdf(bill_id: str):
    # On Windows, WeasyPrint often fails due to missing system libraries.
    # Use ReportLab as a pure-Python fallback.
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception:
        raise HTTPException(500, "Thiếu thư viện tạo PDF (reportlab). Vui lòng cài đặt lại requirements.")
    db = get_db()
    bill = await db.bills.find_one({"_id": bill_id})
    if not bill:
        bill = await db.bills.find_one({"_id": ObjectId(bill_id)})
    if not bill:
        raise HTTPException(404)
    contract = await db.contracts.find_one({"_id": bill.get("contract_id")})
    if not contract:
        contract = await db.contracts.find_one({"_id": ObjectId(bill.get("contract_id"))})
    tenant = None
    room = None
    if contract:
        tenant = await db.tenants.find_one({"_id": contract.get("tenant_id")}) or await db.tenants.find_one({"_id": ObjectId(contract.get("tenant_id"))})
        room = await db.rooms.find_one({"_id": contract.get("room_id")}) or await db.rooms.find_one({"_id": ObjectId(contract.get("room_id"))})
        if tenant:
            try:
                tenant["phone"] = decrypt_value(tenant.get("phone"))
            except Exception:
                pass

    # Backfill water_cost for legacy bills that don't have it.
    try:
        water_cost_val = bill.get("water_cost")
        if water_cost_val is None or int(water_cost_val) == 0:
            bill["water_cost"] = WATER_FEE
    except Exception:
        bill["water_cost"] = WATER_FEE
    # If bill is missing total but has components, compute display total.
    room_price = int(bill.get("room_price", 0) or 0)
    electric_cost = int(bill.get("electric_cost", 0) or 0)
    water_cost = int(bill.get("water_cost", 0) or 0)
    other_cost = int(bill.get("other_cost", 0) or 0)
    total = int(bill.get("total", room_price + electric_cost + water_cost + other_cost) or 0)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Register a Unicode font for Vietnamese (Windows-friendly)
    font_regular = "Helvetica"
    font_bold = "Helvetica-Bold"
    try:
        arial = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
        arial_bold = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arialbd.ttf")
        if os.path.exists(arial) and os.path.exists(arial_bold):
            pdfmetrics.registerFont(TTFont("ArialVN", arial))
            pdfmetrics.registerFont(TTFont("ArialVN-Bold", arial_bold))
            font_regular = "ArialVN"
            font_bold = "ArialVN-Bold"
    except Exception:
        pass

    # Basic layout
    x_margin = 18 * mm
    y = height - 18 * mm

    c.setFont(font_bold, 16)
    c.drawString(x_margin, y, "HÓA ĐƠN")
    y -= 8 * mm

    c.setFont(font_regular, 10)
    c.drawString(x_margin, y, f"Tháng: {bill.get('month','')}")
    status = bill.get("status", "")
    status_vi = "Đã đóng" if status == "paid" else ("Chưa đóng" if status == "unpaid" else str(status))
    c.drawRightString(width - x_margin, y, f"Trạng thái: {status_vi}")
    y -= 10 * mm

    tenant_name = tenant.get("full_name") if tenant else ""
    tenant_phone = tenant.get("phone") if tenant else ""
    room_number = room.get("room_number") if room else ""

    c.setFont(font_bold, 11)
    c.drawString(x_margin, y, "Người thuê:")
    c.setFont(font_regular, 11)
    c.drawString(x_margin + 26 * mm, y, f"{tenant_name}")
    y -= 6 * mm
    c.setFont(font_regular, 10)
    c.drawString(x_margin + 26 * mm, y, f"{tenant_phone}")

    c.setFont(font_bold, 11)
    c.drawRightString(width - x_margin - 26 * mm, y + 6 * mm, "Phòng:")
    c.setFont(font_regular, 11)
    c.drawRightString(width - x_margin, y + 6 * mm, f"{room_number}")
    y -= 12 * mm

    # Table-like lines
    def line_item(label: str, amount: int):
        nonlocal y
        c.setFont(font_regular, 11)
        c.drawString(x_margin, y, label)
        c.drawRightString(width - x_margin, y, money(amount))
        y -= 7 * mm

    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.line(x_margin, y, width - x_margin, y)
    y -= 8 * mm

    line_item("Tiền phòng", room_price)
    line_item("Tiền điện", electric_cost)
    line_item("Tiền nước", water_cost)
    line_item("Khác", other_cost)

    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.line(x_margin, y, width - x_margin, y)
    y -= 8 * mm
    c.setFont(font_bold, 12)
    c.drawString(x_margin, y, "Tổng")
    c.drawRightString(width - x_margin, y, money(total))

    c.showPage()
    c.save()
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf")
