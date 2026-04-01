from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from core.deps import get_db
from bson import ObjectId
import datetime
import os
from jinja2 import Environment, FileSystemLoader

# Thêm thư viện timezone để xử lý giờ Việt Nam
from datetime import timezone, timedelta
# Khởi tạo múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))

from core.template_filters import money
from core.constants import WATER_FEE
from core.flash import redirect_with_flash

router = APIRouter(prefix="/bills", tags=["bills"])

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.filters["money"] = money

# 1. API Render khung HTML cực nhanh (chỉ lấy danh sách hợp đồng cho Dropdown)
@router.get("/")
async def list_bills_html(request: Request, status: str = "all"):
    db = get_db()
    # Lấy tháng hiện tại theo giờ Việt Nam
    default_month = datetime.datetime.now(VN_TZ).strftime("%Y-%m")
    contracts_list = []
    
    try:
        # Dùng Aggregation thay cho N+1 queries
        pipeline = [
            # Biến đổi string room_id và tenant_id thành ObjectId để join
            {"$addFields": {
                "room_obj_id": {"$convert": {"input": "$room_id", "to": "objectId", "onError": None, "onNull": None}},
                "tenant_obj_id": {"$convert": {"input": "$tenant_id", "to": "objectId", "onError": None, "onNull": None}}
            }},
            {"$lookup": {"from": "rooms", "localField": "room_obj_id", "foreignField": "_id", "as": "room_info"}},
            {"$lookup": {"from": "tenants", "localField": "tenant_obj_id", "foreignField": "_id", "as": "tenant_info"}},
            {"$unwind": {"path": "$room_info", "preserveNullAndEmptyArrays": True}},
            {"$unwind": {"path": "$tenant_info", "preserveNullAndEmptyArrays": True}}
        ]
        
        async for c in db.contracts.aggregate(pipeline):
            cid = str(c.get("_id"))
            room_number = c.get("room_info", {}).get("room_number", "")
            tenant_name = c.get("tenant_info", {}).get("full_name", "")
            
            display_text = f"{tenant_name} - Phòng {room_number}".strip(" - ")
            if display_text:
                contracts_list.append({"id": cid, "display": display_text})
                
    except Exception as e:
        # In lỗi rõ ràng ra console thay vì dùng "pass" mù quáng
        print(f"[API_ERROR] list_bills_html: {str(e)}")

    tpl = env.get_template("bills.html")
    html = tpl.render(request=request, default_month=default_month, status=status, contracts=contracts_list)
    return HTMLResponse(content=html)


@router.get("/_data")
async def list_bills_data(status: str = "all"):
    db = get_db()
    match_stage = {}
    if status in ("paid", "unpaid"):
        match_stage["status"] = status

    pipeline = [
        {"$match": match_stage},
        {"$sort": {"created_at": -1}},
        
        # 1. Ép kiểu an toàn contract_id (từ String sang ObjectId)
        {"$addFields": {
            "contract_obj_id": {"$convert": {"input": "$contract_id", "to": "objectId", "onError": None, "onNull": None}},
            "bill_str_id": {"$toString": "$_id"} # Chuẩn bị để lookup payments
        }},
        
        # 2. Lookup Contract
        {"$lookup": {"from": "contracts", "localField": "contract_obj_id", "foreignField": "_id", "as": "contract_info"}},
        {"$unwind": {"path": "$contract_info", "preserveNullAndEmptyArrays": True}},
        
        # 3. Ép kiểu room/tenant ID từ contract
        {"$addFields": {
            "room_obj_id": {"$convert": {"input": "$contract_info.room_id", "to": "objectId", "onError": None, "onNull": None}},
            "tenant_obj_id": {"$convert": {"input": "$contract_info.tenant_id", "to": "objectId", "onError": None, "onNull": None}}
        }},
        
        # 4. Lookup Room & Tenant
        {"$lookup": {"from": "rooms", "localField": "room_obj_id", "foreignField": "_id", "as": "room_info"}},
        {"$unwind": {"path": "$room_info", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "tenants", "localField": "tenant_obj_id", "foreignField": "_id", "as": "tenant_info"}},
        {"$unwind": {"path": "$tenant_info", "preserveNullAndEmptyArrays": True}},
        
        # 5. Lookup Payments (Lấy các khoản đã đóng lẻ tẻ)
        {"$lookup": {"from": "payments", "localField": "bill_str_id", "foreignField": "bill_id", "as": "payments_list"}}
    ]

    bills = []
    try:
        async for b in db.bills.aggregate(pipeline):
            # Lấy thông tin cơ bản an toàn bằng get() với giá trị mặc định, KHÔNG try/except pass
            room_price = b.get("room_price", 0) or 0
            electric_cost = b.get("electric_cost", 0) or 0
            other_cost = b.get("other_cost", 0) or 0
            water_cost = b.get("water_cost", 0) or 0
            total = b.get("total", 0) or 0
            
            if not water_cost:
                water_cost = WATER_FEE
                total = room_price + electric_cost + other_cost + water_cost
                # Cập nhật background nếu thiếu
                await db.bills.update_one({"_id": b["_id"]}, {"$set": {"water_cost": water_cost, "total": total}})

            # Tính toán số tiền đã trả
            paid_amount = b.get("paid_amount")
            if paid_amount is None:
                payments_list = b.get("payments_list", [])
                paid_amount = sum(int(p.get("amount", 0) or 0) for p in payments_list)
            else:
                paid_amount = int(paid_amount)

            # Xử lý thời gian hiển thị (UTC -> VN_TZ)
            paid_at_fmt = ""
            pa = b.get("paid_at")
            if pa:
                if isinstance(pa, str):
                    try:
                        pa = datetime.datetime.fromisoformat(pa.replace('Z', '+00:00'))
                    except ValueError:
                        pa = None
                if isinstance(pa, datetime.datetime):
                    # Nếu đang ở dạng Naive (không có timezone), gán cho nó là UTC
                    if pa.tzinfo is None:
                        pa = pa.replace(tzinfo=timezone.utc)
                    # Chuyển sang giờ Việt Nam
                    pa_vn = pa.astimezone(VN_TZ)
                    paid_at_fmt = pa_vn.strftime('%d/%m/%Y %H:%M')

            # Build dict trả về cho JSON Front-end
            bills.append({
                "id": str(b["_id"]),
                "month": b.get("month", ""),
                "total": total,
                "paid_amount": paid_amount,
                "paid_at_fmt": paid_at_fmt,
                "status": b.get("status", "unpaid"),
                "contract_display": {
                    "tenant_name": b.get("tenant_info", {}).get("full_name", ""),
                    "room_number": b.get("room_info", {}).get("room_number", "")
                }
            })
    except Exception as e:
        print(f"[API_ERROR] list_bills_data: {str(e)}")
        # Có thể raise HTTPException nếu muốn hiển thị lỗi ra FE

    return bills

@router.post("/generate")
async def generate_monthly(
    month: str = Form(...), 
    contract_id: str = Form(...), # Bỏ Form(None) vì bắt buộc
    new_electric_index: int = Form(None) # Thêm tham số này
):
    db = get_db()
    try:
        c = await db.contracts.find_one({"_id": ObjectId(contract_id)})
        if not c:
            return redirect_with_flash('/bills/?status=unpaid', 'Không tìm thấy hợp đồng để tạo hóa đơn.', 'danger')
        
        room_id_val = c.get('room_id')
        room = await db.rooms.find_one({"_id": ObjectId(room_id_val)})
        room_price = int(room.get('price', 0)) if room else 0
        
        # Xử lý lưu chỉ số điện nếu có truyền lên ---
        if new_electric_index is not None:
            old_index = room.get('current_electric_index', 0) if room else 0
            usage = new_electric_index - old_index
            if usage < 0: usage = 0 # Hoặc raise lỗi tùy logic của bạn
            kwh_price = room.get('electric_price', 3500) # Giả sử giá điện lưu ở room
            electric_cost = usage * kwh_price
            
            # Lưu vào db.electric_readings
            await db.electric_readings.insert_one({
                "room_id": str(room_id_val),
                "month": month,
                "old_index": old_index,
                "new_index": new_electric_index,
                "usage": usage,
                "price_per_kwh": kwh_price,
                "total": electric_cost,
                "created_at": datetime.datetime.utcnow()
            })
            
            # Cập nhật lại chỉ số mới cho phòng
            await db.rooms.update_one(
                {"_id": ObjectId(room_id_val)},
                {"$set": {"current_electric_index": new_electric_index}}
            )

        er = await db.electric_readings.find_one({
            "$or": [{"room_id": room_id_val}, {"room_id": str(room_id_val)}],
            "month": month
        })
        
        if er:
            prev_index = er.get('old_index')
            curr_index = er.get('new_index')
            usage = er.get('usage')
            kwh_price = er.get('price_per_kwh')
            electric_cost = er.get('total')
            if not electric_cost:
                electric_cost = int(usage or 0) * int(kwh_price or 0)
        else:
            prev_index = room.get('current_electric_index') if room else None
            curr_index = None
            usage = None
            kwh_price = None
            electric_cost = 0
            
        water_cost = WATER_FEE
        total = room_price + electric_cost + water_cost
        
        bill = {
            "contract_id": str(c.get("_id")), "month": month, 
            "room_price": room_price, "electric_cost": electric_cost, 
            "water_cost": water_cost, "other_cost": 0, "total": total, 
            "status": "unpaid", "created_at": datetime.datetime.utcnow(),
            "prev_index": prev_index, "curr_index": curr_index, 
            "usage": usage, "kwh_price": kwh_price
        }
        await db.bills.insert_one(bill)
        return redirect_with_flash(f"/bills/?status=unpaid", f"Tạo hóa đơn cho hợp đồng thành công.")
            
    except Exception as e:
        print(f"Lỗi tạo hóa đơn: {e}")
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
    
@router.get("/check-electric")
async def check_electric(contract_id: str, month: str):
    db = get_db()
    try:
        c = await db.contracts.find_one({"_id": ObjectId(contract_id)})
        if not c:
            raise HTTPException(404, "Không tìm thấy hợp đồng")
            
        room_id = c.get("room_id")
        room = await db.rooms.find_one({"_id": ObjectId(room_id)})
        
        # Kiểm tra xem tháng này có dữ liệu điện chưa
        er = await db.electric_readings.find_one({
            "$or": [{"room_id": room_id}, {"room_id": str(room_id)}],
            "month": month
        })
        
        if er:
            return {"has_data": True}
            
        old_index = room.get("current_electric_index", 0) if room else 0
        return {"has_data": False, "old_index": old_index}
    except Exception as e:
        raise HTTPException(500, str(e))