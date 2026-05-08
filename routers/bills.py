from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from core.deps import get_db
from core import constants
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
    
    # Load rooms and tenants into memory to build display text without N+1 queries
    rooms_map = {}
    async for r in db.rooms.find({}):
        rooms_map[str(r.get("_id"))] = r
        if r.get("room_number") is not None:
            rooms_map[str(r.get("room_number"))] = r

    tenants_map = {}
    async for t in db.tenants.find({}):
        tenants_map[str(t.get("_id"))] = t

    try:
        async for c in db.contracts.find({}):
            # Determine if contract is active (skip terminated/ended contracts)
            today = datetime.datetime.now(VN_TZ).date()
            # Consider a contract ended ONLY when it has a termination marker
            # (i.e., explicitly terminated). Do not infer ended-ness from end_date.
            term = c.get("termination_date") or c.get("termination") or c.get("termination_date_iso")
            if term:
                ended = True
            else:
                ended = False

            if ended:
                continue

            cid = str(c.get("_id"))
            # Resolve room number via normalized room_id or room_number fallback
            room_number = ""
            rid = c.get("room_id")
            if rid is not None:
                room_doc = None
                try:
                    room_doc = rooms_map.get(str(rid))
                except Exception:
                    room_doc = None
                if not room_doc:
                    try:
                        room_doc = rooms_map.get(str(int(rid)))
                    except Exception:
                        room_doc = rooms_map.get(str(rid))
                if room_doc:
                    room_number = room_doc.get("room_number", "")

            tenant_name = ""
            tid = c.get("tenant_id")
            if tid is not None:
                tenant_doc = tenants_map.get(str(tid))
                if tenant_doc:
                    tenant_name = tenant_doc.get("full_name", "")

            display_text = f"{tenant_name} - Phòng {room_number}".strip(" - ")
            if display_text:
                contracts_list.append({"id": cid, "display": display_text})
    except Exception as e:
        print(f"[API_ERROR] list_bills_html: {str(e)}")

    tpl = env.get_template("bills.html")
    html = tpl.render(request=request, default_month=default_month, status=status, contracts=contracts_list)
    return HTMLResponse(content=html)


@router.get("/_data")
async def list_bills_data(status: str = "all", time_filter: str = "month"):
    db = get_db()
    match_stage = {}
    
    # 1. Logic lọc theo trạng thái
    if status in ("paid", "unpaid"):
        match_stage["status"] = status

    # 2. Logic lọc theo thời gian
    now_vn = datetime.datetime.now(VN_TZ)
    if time_filter == "month":
        match_stage["month"] = now_vn.strftime("%Y-%m")
    elif time_filter == "year":
        match_stage["month"] = {"$regex": f"^{now_vn.strftime('%Y')}-"}
    # Nếu time_filter == "all", không thêm điều kiện lọc month vào match_stage

    pipeline = [
        {"$match": match_stage},
        {"$sort": {"created_at": -1}},
        
        {"$addFields": {
            "contract_obj_id": {"$convert": {"input": "$contract_id", "to": "objectId", "onError": None, "onNull": None}},
            "bill_str_id": {"$toString": "$_id"} 
        }},
        {"$lookup": {"from": "contracts", "localField": "contract_obj_id", "foreignField": "_id", "as": "contract_info"}},
        {"$unwind": {"path": "$contract_info", "preserveNullAndEmptyArrays": True}},
        
        {"$addFields": {
            "room_obj_id": {"$convert": {"input": "$contract_info.room_id", "to": "objectId", "onError": None, "onNull": None}},
            "tenant_obj_id": {"$convert": {"input": "$contract_info.tenant_id", "to": "objectId", "onError": None, "onNull": None}}
        }},
        
        {"$lookup": {"from": "rooms", "localField": "room_obj_id", "foreignField": "_id", "as": "room_info"}},
        {"$unwind": {"path": "$room_info", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "tenants", "localField": "tenant_obj_id", "foreignField": "_id", "as": "tenant_info"}},
        {"$unwind": {"path": "$tenant_info", "preserveNullAndEmptyArrays": True}},
        
        {"$lookup": {"from": "payments", "localField": "bill_str_id", "foreignField": "bill_id", "as": "payments_list"}}
    ]

    bills = []
    try:
        async for b in db.bills.aggregate(pipeline):
            # Normalize fields: support legacy names (rent_amount, electric_amount, water_amount, total_amount)
            try:
                room_price = int(b.get("room_price") or b.get("rent_amount") or 0)
            except Exception:
                room_price = 0
            try:
                electric_cost = int(b.get("electric_cost") or b.get("electric_amount") or b.get("electric") or 0)
            except Exception:
                electric_cost = 0
            try:
                other_cost = int(b.get("other_cost") or 0)
            except Exception:
                other_cost = 0
            try:
                water_cost = int(b.get("water_cost") or b.get("water_amount") or b.get("water") or 0)
            except Exception:
                water_cost = 0

            # Tính lại tổng nợ chuẩn (Không lấy từ b.get("total") vì có thể nó đã bị hàm phía dưới ghi đè thành 0 hoặc số còn lại!)
            full_total = room_price + electric_cost + other_cost + water_cost
            if not water_cost and ("water_cost" not in b):
                 water_cost = WATER_FEE
                 full_total = room_price + electric_cost + other_cost + water_cost

            paid_amount = b.get("paid_amount")
            if paid_amount is None:
                payments_list = b.get("payments_list", [])
                paid_amount = sum(int(p.get("amount", 0) or 0) for p in payments_list)
            else:
                paid_amount = int(paid_amount)
                
            remaining_debt = max(0, full_total - paid_amount)
            correct_status = "paid" if paid_amount >= full_total and full_total > 0 else "unpaid"
            
            # Cập nhật lại db nếu status bị lệch hoặc total bị sai do bug cũ
            db_total = b.get("total")
            if db_total != full_total or b.get("status") != correct_status:
                try:
                    await db.bills.update_one({"_id": b["_id"]}, {"$set": {"total": full_total, "status": correct_status}})
                except:
                    pass

            # Xử lý Lịch sử thanh toán từ schema PaymentRecord
            raw_history = b.get("payment_history", [])
            formatted_history = []
            for ph in raw_history:
                ph_date = ph.get("date")
                ph_date_fmt = ""
                if isinstance(ph_date, datetime.datetime):
                    if ph_date.tzinfo is None:
                        ph_date = ph_date.replace(tzinfo=timezone.utc)
                    ph_date_fmt = ph_date.astimezone(VN_TZ).strftime('%d/%m/%Y %H:%M')
                
                formatted_history.append({
                    "amount": int(ph.get("amount", 0)),
                    "method": ph.get("method", "Chuyển khoản"),
                    "date_fmt": ph_date_fmt
                })

            bills.append({
                "id": str(b["_id"]),
                "month": b.get("month", ""),
                "full_total": full_total,
                "total": remaining_debt, # Frontend renders b.total as "Còn nợ" (Remaining Debt)
                "paid_amount": paid_amount,
                "status": correct_status,
                "payment_history": formatted_history, 
                "contract_display": {
                    "tenant_name": b.get("tenant_info", {}).get("full_name", ""),
                    "room_number": b.get("room_info", {}).get("room_number", "")
                }
            })
    except Exception as e:
        print(f"[API_ERROR] list_bills_data: {str(e)}")

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
        # Robust room lookup (support ObjectId, string id, and room_number)
        room_id_val = c.get('room_id')
        room = None
        if room_id_val is not None:
            try:
                room = await db.rooms.find_one({"_id": ObjectId(str(room_id_val))})
            except Exception:
                room = None

            if not room:
                try:
                    room = await db.rooms.find_one({"_id": room_id_val})
                except Exception:
                    room = None

            if not room:
                # try room_number
                or_clauses = []
                try:
                    or_clauses.append({"room_number": int(room_id_val)})
                except Exception:
                    pass
                try:
                    or_clauses.append({"room_number": str(room_id_val)})
                except Exception:
                    pass
                if or_clauses:
                    try:
                        room = await db.rooms.find_one({"$or": or_clauses})
                    except Exception:
                        room = None

        room_price = int(room.get('price', 0)) if room else 0
        
        # Xử lý lưu chỉ số điện nếu có truyền lên ---
        if new_electric_index is not None:
            old_index = room.get('current_electric_index', 0) if room else 0
            usage = new_electric_index - old_index
            if usage < 0:
                usage = 0
            kwh_price = room.get(constants.PRICE_PER_KWH, 3000) if room else constants.PRICE_PER_KWH
            electric_cost = usage * kwh_price

            # Lưu vào db.electric_readings, use normalized room _id string if available
            save_room_id = None
            if room and room.get("_id") is not None:
                save_room_id = str(room.get("_id"))
            else:
                try:
                    save_room_id = str(room_id_val)
                except Exception:
                    save_room_id = None

            await db.electric_readings.insert_one({
                "room_id": save_room_id,
                "month": month,
                "old_index": old_index,
                "new_index": new_electric_index,
                "usage": usage,
                "price_per_kwh": kwh_price,
                "total": electric_cost,
                "created_at": datetime.datetime.utcnow()
            })

            # Cập nhật lại chỉ số mới cho phòng (use room._id directly if available)
            try:
                if room and room.get("_id") is not None:
                    await db.rooms.update_one({"_id": room.get("_id")}, {"$set": {"current_electric_index": new_electric_index}})
                else:
                    # fallback: attempt to update by string id or room_number
                    try:
                        await db.rooms.update_one({"_id": ObjectId(str(room_id_val))}, {"$set": {"current_electric_index": new_electric_index}})
                    except Exception:
                        try:
                            await db.rooms.update_one({"_id": room_id_val}, {"$set": {"current_electric_index": new_electric_index}})
                        except Exception:
                            pass
            except Exception:
                pass

        # Find electric reading robustly
        er = None
        try:
            or_clauses = []
            if room and room.get("_id") is not None:
                or_clauses.append({"room_id": str(room.get("_id"))})
                or_clauses.append({"room_id": room.get("_id")})
            if room and room.get("room_number") is not None:
                or_clauses.append({"room_id": str(room.get("room_number"))})
                or_clauses.append({"room_id": room.get("room_number")})
            if room_id_val is not None:
                or_clauses.append({"room_id": str(room_id_val)})
                or_clauses.append({"room_id": room_id_val})

            # dedupe
            seen = set()
            uniq_or = []
            for o in or_clauses:
                v = list(o.values())[0]
                key = str(v)
                if key in seen:
                    continue
                seen.add(key)
                uniq_or.append({"room_id": v})

            if uniq_or:
                er = await db.electric_readings.find_one({"$or": uniq_or, "month": month})
            else:
                er = None
        except Exception:
            er = None
        
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
async def pay_bill(
    bill_id: str, 
    amount: int = Form(...), 
    method: str = Form("Chuyển khoản"),
    payment_date: str = Form(None) # Lấy ngày thanh toán từ form
):
    db = get_db()
    try:
        bill = await db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            return redirect_with_flash("/bills/?status=unpaid", "Không tìm thấy hóa đơn.", "danger")
        
        try:
            full_total = int(bill.get("room_price", 0) or 0) + int(bill.get("electric_cost", 0) or 0) + int(bill.get("water_cost", 0) or 0) + int(bill.get("other_cost", 0) or 0)
            if full_total == 0:
                full_total = int(bill.get("total", 0) or 0)
        except:
            full_total = int(bill.get("total", 0) or 0)

        existing_paid = int(bill.get('paid_amount', 0) or 0)
        remaining_debt = full_total - existing_paid

        if amount <= 0:
            return redirect_with_flash(f"/bills/?status={bill.get('status','unpaid')}", "Số tiền phải lớn hơn 0.", "danger")
        if amount > remaining_debt:
            return redirect_with_flash(f"/bills/?status={bill.get('status','unpaid')}", "Số tiền thanh toán không được lớn hơn dư nợ.", "danger")

        # Xử lý ngày thanh toán (Nếu không chọn thì lấy UTC hiện tại)
        if payment_date:
            try:
                # Lấy giờ, phút, giây hiện tại ở VN
                now_vn = datetime.datetime.now(VN_TZ)
                # Chuyển string date thành datetime và gắn giờ hiện tại vào
                p_date = datetime.datetime.strptime(payment_date, "%Y-%m-%d").replace(
                    hour=now_vn.hour, 
                    minute=now_vn.minute, 
                    second=now_vn.second,
                    tzinfo=VN_TZ
                )
            except ValueError:
                p_date = datetime.datetime.now(VN_TZ)
        else:
            p_date = datetime.datetime.now(VN_TZ)

        new_paid = existing_paid + amount
        
        # 1. Cập nhật thông tin tổng quát của Bill (Không thay đổi 'total')
        update_fields = {
            'paid_amount': new_paid,
            'paid_method': method or 'Chuyển khoản',
            'paid_at': p_date, # Cập nhật ngày đóng gần nhất
            'total': full_total # Ghi đè lại nếu có lỗi cũ
        }
        
        if new_paid >= full_total and full_total > 0:
            update_fields['status'] = 'paid'
        else:
            update_fields['status'] = 'unpaid'
            
        remaining = full_total - new_paid
            
        # Ghi nhận lần thanh toán này vào mảng payment_history của Bill
        new_payment_record = {
            "amount": amount,
            "method": method,
            "date": p_date,
            "recorded_at": datetime.datetime.utcnow()
        }

        await db.bills.update_one(
            {"_id": ObjectId(bill_id)}, 
            {
                "$set": update_fields,
                "$push": {"payment_history": new_payment_record} # Thêm vào lịch sử
            }
        )

        # 2. Thêm 1 dòng vào collection `payments` để biểu đồ Doanh Thu thống kê được
        await db.payments.insert_one({
            "bill_id": str(bill_id),
            "amount": amount,
            "method": method,
            "payment_date": p_date, # Đây là trường dashboard.py sẽ dùng để vẽ biểu đồ
            "created_at": datetime.datetime.utcnow()
        })

        return redirect_with_flash(f"/bills/?status={ 'paid' if remaining==0 else 'unpaid'}", "Ghi nhận thanh toán thành công.")
    except Exception as e:
        print(f"Lỗi thanh toán: {e}")
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

        # 1. BẮT BUỘC: Xóa tất cả các lịch sử thanh toán (payments) mồ côi liên kết với Hóa đơn này
        await db.payments.delete_many({"bill_id": str(bill_id)})

        # 2. Sau đó mới tiến hành Xóa Hóa đơn
        await db.bills.delete_one({"_id": ObjectId(bill_id)})
        
        return redirect_with_flash(f"/bills/?status={redirect_status}", "Xóa hóa đơn và các giao dịch liên quan thành công.")
    except Exception as e:
        print(f"Lỗi xóa hóa đơn: {e}")
        return redirect_with_flash("/bills/", "Xóa hóa đơn thất bại.", "danger")
    
@router.get("/check-electric")
async def check_electric(contract_id: str, month: str):
    db = get_db()
    try:
        # Find contract robustly (accept both ObjectId and string id)
        c = None
        try:
            c = await db.contracts.find_one({"_id": ObjectId(contract_id)})
        except Exception:
            c = await db.contracts.find_one({"_id": contract_id})

        if not c:
            raise HTTPException(404, "Không tìm thấy hợp đồng")

        room_id = c.get("room_id")
        room = None

        # Try multiple strategies to find the room (ObjectId, string id, room_number)
        if room_id is not None:
            # 1) Try ObjectId lookup
            try:
                room = await db.rooms.find_one({"_id": ObjectId(str(room_id))})
            except Exception:
                room = None

            # 2) Try exact string id
            if not room:
                try:
                    room = await db.rooms.find_one({"_id": room_id})
                except Exception:
                    room = None

            # 3) Try room_number lookups (both numeric and string)
            if not room:
                or_clauses = []
                try:
                    or_clauses.append({"room_number": int(room_id)})
                except Exception:
                    pass
                try:
                    or_clauses.append({"room_number": str(room_id)})
                except Exception:
                    pass
                if or_clauses:
                    try:
                        room = await db.rooms.find_one({"$or": or_clauses})
                    except Exception:
                        room = None

        # Build a robust query to find electric reading for this room for the given month
        er = None
        try:
            or_clauses = []
            # Prefer normalized room._id if available
            if room:
                rid = room.get("_id")
                if rid is not None:
                    or_clauses.append({"room_id": str(rid)})
                    or_clauses.append({"room_id": rid})
                rn = room.get("room_number")
                if rn is not None:
                    or_clauses.append({"room_id": str(rn)})
                    or_clauses.append({"room_id": rn})
            # Fallback to contract.room_id variants
            if room_id is not None:
                or_clauses.append({"room_id": str(room_id)})
                or_clauses.append({"room_id": room_id})

            # Remove duplicates while preserving order
            seen = set()
            uniq_or = []
            for o in or_clauses:
                v = list(o.values())[0]
                key = str(v)
                if key in seen:
                    continue
                seen.add(key)
                uniq_or.append({"room_id": v})

            if uniq_or:
                er = await db.electric_readings.find_one({"$or": uniq_or, "month": month})
            else:
                # Last resort: try matching by month only (should be rare)
                er = None
        except Exception:
            er = None

        if er:
            return {"has_data": True}

        old_index = room.get("current_electric_index", 0) if room else 0
        return {"has_data": False, "old_index": old_index}
    except Exception as e:
        raise HTTPException(500, str(e))