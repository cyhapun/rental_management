from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from app.deps import get_db
from bson import ObjectId
import datetime
import os
from jinja2 import Environment, FileSystemLoader

from app.template_filters import money
from app.constants import WATER_FEE
from app.flash import redirect_with_flash

router = APIRouter(prefix="/bills", tags=["bills"])

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.filters["money"] = money


@router.get("/")
async def list_bills(request: Request, status: str = "unpaid"):
    db = get_db()
    q = {}
    if status in ("paid", "unpaid"):
        q["status"] = status
    cursor = db.bills.find(q).sort("created_at", -1)
    bills = []
    async for b in cursor:
        b["id"] = str(b.get("_id"))
        # Backfill water_cost for legacy bills that don't have it.
        if b.get("water_cost") is None or int(b.get("water_cost") or 0) == 0:
            room_price = int(b.get("room_price", 0) or 0)
            electric_cost = int(b.get("electric_cost", 0) or 0)
            other_cost = int(b.get("other_cost", 0) or 0)
            new_total = int(b.get("total", room_price + electric_cost + other_cost) or 0) + WATER_FEE
            await db.bills.update_one(
                {"_id": ObjectId(b["id"])},
                {"$set": {"water_cost": WATER_FEE, "total": new_total}},
            )
            b["water_cost"] = WATER_FEE
            b["total"] = new_total
        # attach contract -> tenant + room for display
        try:
            contract = await db.contracts.find_one({"_id": ObjectId(b.get("contract_id"))})
        except Exception:
            contract = None
        tenant_name = None
        room_number = None
        if contract:
            try:
                room = await db.rooms.find_one({"_id": ObjectId(contract.get("room_id"))})
            except Exception:
                room = None
            if room:
                room_number = room.get("room_number")
            try:
                tenant = await db.tenants.find_one({"_id": ObjectId(contract.get("tenant_id"))})
            except Exception:
                tenant = None
            if tenant:
                tenant_name = tenant.get("full_name")
        b["contract_display"] = {
            "tenant_name": tenant_name,
            "room_number": room_number,
        }
        bills.append(b)
    # default month = current month (YYYY-MM) for generate form
    default_month = datetime.date.today().strftime("%Y-%m")
    tpl = env.get_template("bills.html")
    html = tpl.render(request=request, bills=bills, default_month=default_month, status=status)
    return HTMLResponse(content=html)


@router.post("/generate")
async def generate_monthly(month: str = Form(...)):
    db = get_db()
    try:
        cursor = db.contracts.find({})
        created = 0
        async for c in cursor:
            room = await db.rooms.find_one({"_id": ObjectId(c.get("room_id"))})
            room_price = int(room.get("price", 0)) if room else 0
            er = await db.electric_readings.find_one({"room_id": c.get("room_id"), "month": month})
            electric_cost = er.get("total", 0) if er else 0
            water_cost = WATER_FEE
            total = room_price + electric_cost + water_cost
            bill = {"contract_id": str(c.get("_id")), "month": month, "room_price": room_price, "electric_cost": electric_cost, "water_cost": water_cost, "other_cost": 0, "total": total, "status": "unpaid", "created_at": datetime.datetime.utcnow()}
            await db.bills.insert_one(bill)
            created += 1
        return redirect_with_flash(f"/bills/?status=unpaid", f"Tạo hóa đơn thành công ({created} hóa đơn).")
    except Exception:
        return redirect_with_flash("/bills/?status=unpaid", "Tạo hóa đơn thất bại.", "danger")


@router.post("/{bill_id}/pay")
async def pay_bill(bill_id: str, amount: int = Form(...), method: str = Form("cash")):
    db = get_db()
    try:
        bill = await db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            return redirect_with_flash("/bills/?status=unpaid", "Không tìm thấy hóa đơn.", "danger")
        if amount >= bill.get("total", 0):
            await db.bills.update_one({"_id": ObjectId(bill_id)}, {"$set": {"status": "paid"}})
        await db.payments.insert_one({"bill_id": bill_id, "amount": amount, "payment_date": datetime.datetime.utcnow(), "method": method})
        return redirect_with_flash("/bills/?status=unpaid", "Thanh toán thành công.")
    except Exception:
        return redirect_with_flash("/bills/?status=unpaid", "Thanh toán thất bại.", "danger")


@router.post("/{bill_id}/delete")
async def delete_bill(bill_id: str):
    db = get_db()
    try:
        bill = await db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            return redirect_with_flash("/bills/", "Không tìm thấy hóa đơn.", "danger")

        bill_status = bill.get("status", "unpaid")
        redirect_status = bill_status if bill_status in ("paid", "unpaid") else "unpaid"

        # Remove related payments if present
        try:
            await db.payments.delete_many({"bill_id": bill_id})
        except Exception:
            pass

        await db.bills.delete_one({"_id": ObjectId(bill_id)})
        return redirect_with_flash(f"/bills/?status={redirect_status}", "Xóa hóa đơn thành công.")
    except Exception:
        return redirect_with_flash("/bills/", "Xóa hóa đơn thất bại.", "danger")
