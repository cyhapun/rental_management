from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from core.deps import get_db
from bson import ObjectId
import datetime
import os
from jinja2 import Environment, FileSystemLoader

from core.template_filters import money
from core import constants
from core.flash import redirect_with_flash

router = APIRouter(prefix="/bills", tags=["bills"])

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.filters["money"] = money

# 1. API Render khung HTML cực nhanh (chỉ lấy danh sách hợp đồng cho Dropdown)
@router.get("/")
async def list_bills_html(request: Request, status: str = "all"):
    db = get_db()
    default_month = datetime.date.today().strftime("%Y-%m")
    contracts_list = []
    try:
        ccur = db.contracts.find({})
        async for c in ccur:
            cid = str(c.get("_id"))
            tenant_name = None
            room_number = None
            try:
                room = await db.rooms.find_one({"_id": ObjectId(c.get("room_id"))})
            except Exception:
                room = None
            if room:
                room_number = room.get("room_number")
            try:
                tenant = await db.tenants.find_one({"_id": ObjectId(c.get("tenant_id"))})
            except Exception:
                tenant = None
            if tenant:
                tenant_name = tenant.get("full_name")
            contracts_list.append({"id": cid, "display": (f"{tenant_name or ''} - Phòng {room_number or ''}").strip()})
    except Exception:
        contracts_list = []

    tpl = env.get_template("bills.html")
    # Trả về HTML trống cho phần bảng
    html = tpl.render(request=request, default_month=default_month, status=status, contracts=contracts_list)
    return HTMLResponse(content=html)


# 2. API Trả về Data JSON để JS tự vẽ bảng
@router.get("/_data")
async def list_bills_data(status: str = "all"):
    db = get_db()
    q = {}
    if status in ("paid", "unpaid"):
        q["status"] = status
    cursor = db.bills.find(q).sort("created_at", -1)
    bills = []
    async for b in cursor:
        b["id"] = str(b.get("_id"))
        bills.append(b)

    try:
        ids_missing = [b.get("id") for b in bills if not b.get("paid_amount")]
        payments_map = {}
        if ids_missing:
            pc = db.payments.find({"bill_id": {"$in": ids_missing}})
            async for p in pc:
                try:
                    bid = p.get("bill_id")
                    amt = int(p.get("amount", 0) or 0)
                    payments_map[bid] = payments_map.get(bid, 0) + amt
                except Exception:
                    pass
        for b in bills:
            if b.get("paid_amount") is not None:
                try:
                    b["paid_amount"] = int(b.get("paid_amount") or 0)
                except Exception:
                    b["paid_amount"] = 0
            else:
                b["paid_amount"] = payments_map.get(b.get("id"), 0)
            
            # Xử lý ngày tháng thành string an toàn cho JSON
            try:
                pa = b.get('paid_at')
                if pa:
                    if isinstance(pa, datetime.datetime) or isinstance(pa, datetime.date):
                        b['paid_at_fmt'] = pa.strftime('%d/%m/%Y %H:%M')
                    else:
                        b['paid_at_fmt'] = datetime.datetime.fromisoformat(str(pa)).strftime('%d/%m/%Y %H:%M')
                else:
                    b['paid_at_fmt'] = ''
            except Exception:
                b['paid_at_fmt'] = ''
    except Exception:
        for b in bills:
            b["paid_amount"] = int(b.get("paid_amount") or 0)
            b['paid_at_fmt'] = ''

    async def _resolve_document(collection, doc_id):
        if not doc_id: return None
        try:
            d = await collection.find_one({"_id": doc_id})
            if d: return d
        except Exception: pass
        try:
            d = await collection.find_one({"_id": ObjectId(doc_id)})
            if d: return d
        except Exception: pass
        return None

    for b in bills:
        try:
            if b.get("water_cost") is None or int(b.get("water_cost") or 0) == 0:
                room_price = int(b.get("room_price", 0) or 0)
                electric_cost = int(b.get("electric_cost", 0) or 0)
                other_cost = int(b.get("other_cost", 0) or 0)
                new_total = int(b.get("total", room_price + electric_cost + other_cost) or 0) + WATER_FEE
                try:
                    await db.bills.update_one({"_id": ObjectId(b["id"])}, {"$set": {"water_cost": WATER_FEE, "total": new_total}})
                except Exception:
                    pass
                b["water_cost"] = WATER_FEE
                b["total"] = new_total
        except Exception:
            pass

        tenant_name = None
        room_number = None
        contract = await _resolve_document(db.contracts, b.get("contract_id"))
        if contract:
            room = await _resolve_document(db.rooms, contract.get("room_id"))
            if room:
                room_number = room.get("room_number")
            tenant = await _resolve_document(db.tenants, contract.get("tenant_id"))
            if tenant:
                tenant_name = tenant.get("full_name")
        b["contract_display"] = {"tenant_name": tenant_name, "room_number": room_number}
        
        # Bỏ ObjectId và datetime để chuẩn hóa thành JSON
        b.pop('_id', None)
        if 'created_at' in b:
            b['created_at'] = str(b['created_at'])
        if 'paid_at' in b:
            b.pop('paid_at', None)

    return bills


@router.post("/generate")
async def generate_monthly(month: str = Form(...), contract_id: str = Form(None)):
    db = get_db()
    try:
        created = 0
        if contract_id:
            try:
                c = await db.contracts.find_one({"_id": ObjectId(contract_id)})
            except Exception:
                c = None
            if not c:
                return redirect_with_flash('/bills/?status=unpaid', 'Không tìm thấy hợp đồng để tạo hóa đơn.', 'danger')
            
            room_price = 0
            room_id_val = c.get('room_id')
            room = None
            try:
                room = await db.rooms.find_one({"_id": ObjectId(room_id_val)})
                room_price = int(room.get('price', 0)) if room else 0
            except Exception:
                pass
            
            er = await db.electric_readings.find_one({
                "$or": [{"room_id": room_id_val}, {"room_id": str(room_id_val)}],
                "month": month
            })
            
            electric_cost = er.get('total', 0) if er else 0
            
            if er:
                prev_index = er.get('old_index')
                curr_index = er.get('new_index')
                usage = er.get('usage')
                kwh_price = er.get('price_per_kwh')
            else:
                prev_index = room.get('current_electric_index') if room else None
                curr_index = None
                usage = None
                kwh_price = None
                
            water_cost = WATER_FEE
            total = room_price + electric_cost + water_cost
            bill = {"contract_id": str(c.get("_id")), "month": month, "room_price": room_price, "electric_cost": electric_cost, "water_cost": water_cost, "other_cost": 0, "total": total, "status": "unpaid", "created_at": datetime.datetime.utcnow(),
                    "prev_index": prev_index, "curr_index": curr_index, "usage": usage, "kwh_price": kwh_price}
            await db.bills.insert_one(bill)
            created = 1
            return redirect_with_flash(f"/bills/?status=unpaid", f"Tạo hóa đơn cho hợp đồng thành công.")
        else:
            cursor = db.contracts.find({})
            async for c in cursor:
                room_id_val = c.get("room_id")
                room = None
                try:
                    room = await db.rooms.find_one({"_id": ObjectId(room_id_val)})
                    room_price = int(room.get("price", 0)) if room else 0
                except Exception:
                    room_price = 0
                
                er = await db.electric_readings.find_one({
                    "$or": [{"room_id": room_id_val}, {"room_id": str(room_id_val)}],
                    "month": month
                })
                
                electric_cost = er.get("total", 0) if er else 0
                
                if er:
                    prev_index = er.get('old_index')
                    curr_index = er.get('new_index')
                    usage = er.get('usage')
                    kwh_price = er.get('price_per_kwh')
                else:
                    prev_index = room.get('current_electric_index') if room else None
                    curr_index = None
                    usage = None
                    kwh_price = None
                    
                water_cost = WATER_FEE
                total = room_price + electric_cost + water_cost
                bill = {"contract_id": str(c.get("_id")), "month": month, "room_price": room_price, "electric_cost": electric_cost, "water_cost": water_cost, "other_cost": 0, "total": total, "status": "unpaid", "created_at": datetime.datetime.utcnow(),
                    "prev_index": prev_index, "curr_index": curr_index, "usage": usage, "kwh_price": kwh_price}
                await db.bills.insert_one(bill)
                created += 1
            return redirect_with_flash(f"/bills/?status=unpaid", f"Tạo hóa đơn thành công ({created} hóa đơn).")
    except Exception:
        return redirect_with_flash("/bills/?status=unpaid", "Tạo hóa đơn thất bại.", "danger")


@router.post("/{bill_id}/pay")
async def pay_bill(bill_id: str, amount: int = Form(...), method: str = Form("Chuyển khoản")):
    db = get_db()
    try:
        bill = await db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            return redirect_with_flash("/bills/?status=unpaid", "Không tìm thấy hóa đơn.", "danger")
        total_due = int(bill.get("total", 0) or 0)
        if amount <= 0:
            return redirect_with_flash(f"/bills/?status={bill.get('status','unpaid')}", "Số tiền phải lớn hơn 0.", "danger")
        if amount > total_due:
            return redirect_with_flash(f"/bills/?status={bill.get('status','unpaid')}", "Số tiền thanh toán không được lớn hơn tổng tiền.", "danger")

        remaining = total_due - amount
        existing_paid = int(bill.get('paid_amount', 0) or 0)
        new_paid = existing_paid + amount
        update_fields = {
            'paid_amount': new_paid,
            'paid_method': method or 'Chuyển khoản',
            'paid_at': datetime.datetime.utcnow(),
        }
        if new_paid >= total_due:
            update_fields['status'] = 'paid'
            update_fields['total'] = 0
        else:
            update_fields['total'] = total_due - new_paid
        await db.bills.update_one({"_id": ObjectId(bill_id)}, {"$set": update_fields})

        return redirect_with_flash(f"/bills/?status={ 'paid' if remaining==0 else 'unpaid'}", "Thanh toán thành công.")
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

        await db.bills.delete_one({"_id": ObjectId(bill_id)})
        return redirect_with_flash(f"/bills/?status={redirect_status}", "Xóa hóa đơn thành công.")
    except Exception:
        return redirect_with_flash("/bills/", "Xóa hóa đơn thất bại.", "danger")