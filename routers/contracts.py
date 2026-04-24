from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from core.deps import get_db
from bson import ObjectId
import datetime
import os
from jinja2 import Environment, FileSystemLoader

from core.security import decrypt_value, mask_cccd, hash_value
from core import constants
from core.template_filters import money
from core.flash import redirect_with_flash

router = APIRouter(prefix="/contracts", tags=["contracts"])

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.filters["money"] = money

async def _find_room_by_number(db, room_number_value):
    if room_number_value is None:
        return None
    room_str = str(room_number_value).strip()
    candidates = [room_str]
    try:
        candidates.append(int(room_str))
    except Exception:
        pass
    for c in candidates:
        room_doc = await db.rooms.find_one({"room_number": c})
        if room_doc:
            return room_doc
    return None

def _is_active_contract(contract_doc: dict, today: datetime.date) -> bool:
    # If contract has a termination_date (immediate termination), treat it as inactive
    term = contract_doc.get("termination_date")
    if term:
        try:
            term_date = datetime.date.fromisoformat(str(term))
            if term_date <= today:
                return False
        except Exception:
            pass

    # Hợp đồng được chấm dứt mới kết thúc, còn thời gian trong "thời hạn" (end_date) không được dùng để đưa về báo kết thúc.
    return True

def _contract_order_key(contract_doc: dict):
    start = contract_doc.get("start_date")
    try:
        start_key = datetime.date.fromisoformat(str(start))
    except Exception:
        start_key = datetime.date.min
    return (start_key, str(contract_doc.get("_id")))

def _next_due_date(start_date: datetime.date, today: datetime.date) -> datetime.date:
    day = start_date.day
    year = today.year
    month = today.month
    while True:
        try:
            candidate = datetime.date(year, month, day)
        except ValueError:
            if month == 12:
                next_first = datetime.date(year + 1, 1, 1)
            else:
                next_first = datetime.date(year, month + 1, 1)
            candidate = next_first - datetime.timedelta(days=1)
        if candidate >= today:
            return candidate
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

async def _normalize_room_id_to_oid_str(db, room_id_value):
    if room_id_value is None:
        return None
    rid_str = str(room_id_value)
    try:
        ObjectId(rid_str)
        return rid_str
    except Exception:
        room_doc = await _find_room_by_number(db, rid_str)
        if room_doc:
            return str(room_doc.get("_id"))
    return None

async def _refresh_room_statuses(db):
    latest_by_room = {}
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).date()
    
    cursor = db.contracts.find({})
    async for c in cursor:
        if not _is_active_contract(c, today):
            continue
            
        rid_norm = await _normalize_room_id_to_oid_str(db, c.get("room_id"))
        if not rid_norm:
            continue
        current = latest_by_room.get(rid_norm)
        if (not current) or (_contract_order_key(c) > _contract_order_key(current)):
            latest_by_room[rid_norm] = c
            
    occupied_room_ids = set(latest_by_room.keys())

    rooms_cursor = db.rooms.find({})
    async for r in rooms_cursor:
        rid = str(r.get("_id"))
        new_status = "occupied" if rid in occupied_room_ids else "available"
        if r.get("status") != new_status:
            await db.rooms.update_one({"_id": r.get("_id")}, {"$set": {"status": new_status}})

async def _normalize_contract_refs(db):
    cursor = db.contracts.find({})
    async for c in cursor:
        updates = {}
        rid = c.get("room_id")
        if rid is not None:
            if isinstance(rid, ObjectId):
                updates["room_id"] = str(rid)
            else:
                rid_str = str(rid)
                try:
                    ObjectId(rid_str)
                    updates["room_id"] = rid_str
                except Exception:
                    room_doc = await _find_room_by_number(db, rid_str)
                    if room_doc:
                        updates["room_id"] = str(room_doc.get("_id"))

        tid = c.get("tenant_id")
        if tid is not None:
            if isinstance(tid, ObjectId):
                updates["tenant_id"] = str(tid)
            else:
                tid_str = str(tid)
                try:
                    ObjectId(tid_str)
                    updates["tenant_id"] = tid_str
                except Exception:
                    cccd_h = hash_value(tid_str)
                    tenant_doc = None
                    if cccd_h:
                        tenant_doc = await db.tenants.find_one({"cccd_hash": cccd_h})
                    if not tenant_doc:
                        tenant_doc = await db.tenants.find_one({"cccd": tid_str})
                    if tenant_doc:
                        updates["tenant_id"] = str(tenant_doc.get("_id"))

        if updates:
            await db.contracts.update_one({"_id": c.get("_id")}, {"$set": updates})

# 1. API Trả về khung HTML (Load cực nhanh)
@router.get("/")
async def list_contracts(request: Request):
    db = get_db()
    # Chỉ load danh sách phòng và khách thuê cho Dropdown Modal
    tenants = []
    async for t in db.tenants.find({}).sort("full_name", 1):
        t["id"] = str(t.get("_id"))
        tenants.append({
            "id": t.get("id"),
            "full_name": t.get("full_name"),
            "phone": decrypt_value(t.get("phone")),
            "cccd": mask_cccd(decrypt_value(t.get("cccd"))),
        })
        
    rooms = []
    active_room_ids = []
    latest_by_room = {}
    # Lọc chỉ các hợp đồng còn hiệu lực khi tính phòng đang thuê
    today_vn_calc = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).date()
    async for c in db.contracts.find({}):
        if not _is_active_contract(c, today_vn_calc):
            continue
        rid_norm = await _normalize_room_id_to_oid_str(db, c.get("room_id"))
        if rid_norm:
            current = latest_by_room.get(rid_norm)
            if (not current) or (_contract_order_key(c) > _contract_order_key(current)):
                latest_by_room[rid_norm] = c
    active_room_ids = list(latest_by_room.keys())

    async for r in db.rooms.find({}).sort("room_number", 1):
        r["id"] = str(r.get("_id"))
        rooms.append({"id": r.get("id"), "room_number": r.get("room_number"), "price": r.get("price"), "status": r.get("status")})

    today_vn = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    today_str = today_vn.date().isoformat()
    tpl = env.get_template("contracts.html")
    html = tpl.render(
        request=request,
        tenants=tenants,
        rooms=rooms,
        active_room_ids=active_room_ids,
        today=today_str,
    )
    return HTMLResponse(content=html)

# 2. API Trả về dữ liệu JSON (Đã Tối ưu hóa N+1 Query triệt để)
@router.get("/_data")
async def list_contracts_data(request: Request):
    db = get_db()
    
    # Tải sẵn Dữ liệu Master (Rooms và Tenants) vào RAM Cache (Dictionary)
    all_rooms = []
    async for r in db.rooms.find({}):
        all_rooms.append(r)
    rooms_map_by_id = {str(r["_id"]): r for r in all_rooms}
    rooms_map_by_number = {str(r.get("room_number")): r for r in all_rooms if r.get("room_number")}

    all_tenants = []
    async for t in db.tenants.find({}):
        all_tenants.append(t)
    tenants_map_by_id = {str(t["_id"]): t for t in all_tenants}
    
    # Hàm Tra cứu Room nội bộ siêu nhanh (Không chạm Database)
    def get_room_id_str(val):
        if not val: return None
        val_str = str(val)
        if val_str in rooms_map_by_id: return val_str
        if val_str in rooms_map_by_number: return str(rooms_map_by_number[val_str]["_id"])
        return None

    all_contracts = []
    async for c in db.contracts.find({}):
        all_contracts.append(c)

    # Xác định ngày hôm nay (theo múi giờ VN) trước khi tính toán hợp đồng active
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).date()

    # Tìm hợp đồng active mới nhất cho từng phòng
    latest_by_room = {}
    for c in all_contracts:
        if not _is_active_contract(c, today):
            continue
        rid_norm = get_room_id_str(c.get("room_id"))
        if not rid_norm:
            continue
        current = latest_by_room.get(rid_norm)
        if (not current) or (_contract_order_key(c) > _contract_order_key(current)):
            latest_by_room[rid_norm] = c

    latest_contract_ids = {str(v["_id"]) for v in latest_by_room.values()}
    contract_ids = list(latest_contract_ids)
    active_room_ids = set(latest_by_room.keys())
    active_tenant_ids = set()

    # Aggregation lấy toàn bộ Hóa Đơn mới nhất của TẤT CẢ các phòng trong 1 Query duy nhất
    bills_map = {}
    if contract_ids:
        pipeline_bills = [
            {"$match": {"contract_id": {"$in": contract_ids}}},
            {"$sort": {"month": -1, "created_at": -1, "_id": -1}},
            {"$group": {"_id": "$contract_id", "latest_bill": {"$first": "$$ROOT"}}}
        ]
        async for b_group in db.bills.aggregate(pipeline_bills):
            bills_map[str(b_group["_id"])] = b_group["latest_bill"]

    # Aggregation lấy Số điện mới nhất của TẤT CẢ các phòng trong 1 Query duy nhất
    er_map = {}
    pipeline_er = [
        {"$sort": {"month": -1, "_id": -1}},
        {"$group": {"_id": "$room_id", "latest_er": {"$first": "$$ROOT"}}}
    ]
    async for er_group in db.electric_readings.aggregate(pipeline_er):
        er_map[str(er_group["_id"])] = er_group["latest_er"]

    def _to_iso_date(d):
        if not d: return None
        try: return datetime.date.fromisoformat(str(d)).isoformat()
        except Exception:
            try:
                dt = datetime.datetime.fromisoformat(str(d))
                if dt.tzinfo is None: dt = dt + datetime.timedelta(hours=7)
                return dt.date().isoformat()
            except Exception: return None

    def _fmt_date_iso(d):
        if not d: return None
        try: return datetime.date.fromisoformat(str(d)).strftime("%d/%m/%Y")
        except Exception:
            try:
                dt = datetime.datetime.fromisoformat(str(d))
                if dt.tzinfo is None: dt = dt + datetime.timedelta(hours=7)
                else: dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
                return dt.strftime("%d/%m/%Y")
            except Exception: return str(d)

    contracts_result = []
    
    # Mapping Data trực tiếp trên RAM (O(1) Access) thay vì Query DB liên tục
    for c in all_contracts:
        c_id = str(c["_id"])
        c["id"] = c_id
        c["is_active"] = c_id in latest_contract_ids
        
        rid_norm = get_room_id_str(c.get("room_id"))
        tid_str = str(c.get("tenant_id")) if c.get("tenant_id") else None

        if c["is_active"]:
            if rid_norm: active_room_ids.add(rid_norm)
            if tid_str: active_tenant_ids.add(tid_str)

        t_doc = tenants_map_by_id.get(tid_str)
        if t_doc:
            c["tenant"] = {
                "full_name": t_doc.get("full_name"),
                "phone": decrypt_value(t_doc.get("phone")),
                "id": str(t_doc.get("_id")),
                "cccd": mask_cccd(decrypt_value(t_doc.get("cccd"))),
            }

        r_doc = rooms_map_by_id.get(rid_norm)
        if r_doc:
            c["room"] = {
                "room_number": r_doc.get("room_number"),
                "price": r_doc.get("price"),
                "status": r_doc.get("status"),
                "id": str(r_doc.get("_id")),
                "current_electric_index": r_doc.get("current_electric_index")
            }

        latest_er = None
        if rid_norm in er_map:
            latest_er = er_map[rid_norm]
        elif r_doc and str(r_doc.get("room_number")) in er_map:
            latest_er = er_map[str(r_doc.get("room_number"))]
            
        if latest_er:
            new_idx = int(latest_er.get("new_index", 0))
            old_idx = int(latest_er.get("old_index", 0))
            c["electric"] = {
                "current_kwh": new_idx,
                "used_kwh": max(0, new_idx - old_idx),
                "month": latest_er.get("month")
            }
        else:
            c["electric"] = {
                "current_kwh": int(r_doc.get("current_electric_index", 0)) if r_doc else 0,
                "used_kwh": 0,
                "month": None
            }

        latest_bill = bills_map.get(c_id)
        if latest_bill:
            c["rent_payment_status"] = latest_bill.get("status", "unpaid")
            c["rent_payment_month"] = latest_bill.get("month")
        else:
            c["rent_payment_status"] = "no_bill"
            c["rent_payment_month"] = None

        c["start_date_iso"] = _to_iso_date(c.get("start_date"))
        c["end_date_iso"] = _to_iso_date(c.get("end_date"))
        c["start_date"] = _fmt_date_iso(c.get("start_date"))
        c["end_date"] = _fmt_date_iso(c.get("end_date"))

        c.pop('_id', None)
        contracts_result.append(c)

    upcoming_dues = []
    for c in contracts_result:
        if not c.get("is_active"): continue
        start_iso = c.get("start_date_iso")
        if not start_iso: continue
        try: start_date = datetime.date.fromisoformat(str(start_iso))
        except Exception: continue
        due = _next_due_date(start_date, today)
        days_left = (due - today).days
        if 0 <= days_left <= 2:
            entry = {
                "room_number": c.get("room", {}).get("room_number") if c.get("room") else c.get("room_id"),
                "tenant_name": c.get("tenant", {}).get("full_name") if c.get("tenant") else c.get("tenant_id"),
                "due_date": due.isoformat(),
                "days_left": days_left
            }
            upcoming_dues.append(entry)
            
    upcoming_dues.sort(key=lambda x: x["days_left"])

    return {
        "contracts": contracts_result,
        "upcoming_dues": upcoming_dues,
        "active_rooms_count": len(active_room_ids),
        "active_tenants_count": len(active_tenant_ids)
    }

@router.post("/create")
async def create_contract(request: Request, tenant_id: str = Form(...), room_id: str = Form(...), start_date: str = Form(...), end_date: str = Form(None), contract_type: str = Form(None), deposit: int = Form(0)):
    db = get_db()
    if getattr(request.state, "user_role", None) not in ("admin", "manager"):
        return redirect_with_flash("/dashboard", "Bạn không có quyền tạo hợp đồng", "danger")
    try:
        tenant_oid = ObjectId(tenant_id)
        room_oid = ObjectId(room_id)
    except Exception:
        return redirect_with_flash("/contracts/", "Dữ liệu phòng/người thuê không hợp lệ.", "danger")
    try:
        tenant = await db.tenants.find_one({"_id": tenant_oid})
        if not tenant:
            return redirect_with_flash("/contracts/", "Không tìm thấy người thuê.", "danger")
        room = await db.rooms.find_one({"_id": room_oid})
        if not room:
            return redirect_with_flash("/contracts/", "Không tìm thấy phòng.", "danger")

        contract = {
            "tenant_id": str(tenant_oid),
            "room_id": str(room_oid),
            "start_date": start_date,
            "end_date": end_date,
            "contract_type": contract_type,
            "deposit": deposit
        }
        await db.contracts.insert_one(contract)
        await _refresh_room_statuses(db)
        return redirect_with_flash("/contracts/", "Tạo hợp đồng thành công.")
    except Exception:
        return redirect_with_flash("/contracts/", "Tạo hợp đồng thất bại.", "danger")

@router.post("/{contract_id}/update")
async def update_contract(
    request: Request,
    contract_id: str,
    tenant_id: str = Form(...),
    room_id: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(None),
    contract_type: str = Form(None),
    deposit: int = Form(0),
):
    db = get_db()
    if getattr(request.state, "user_role", None) not in ("admin", "manager"):
        return redirect_with_flash("/dashboard", "Bạn không có quyền cập nhật hợp đồng", "danger")
    try:
        tenant_oid = ObjectId(tenant_id)
        room_oid = ObjectId(room_id)
        contract_oid = ObjectId(contract_id)
    except Exception:
        return redirect_with_flash("/contracts/", "Dữ liệu hợp đồng không hợp lệ.", "danger")
    try:
        await db.contracts.update_one(
            {"_id": contract_oid},
            {
                "$set": {
                    "tenant_id": str(tenant_oid),
                    "room_id": str(room_oid),
                    "start_date": start_date,
                    "end_date": end_date,
                    "contract_type": contract_type,
                    "deposit": deposit,
                }
            },
        )
        await _refresh_room_statuses(db)
        return redirect_with_flash("/contracts/", "Cập nhật hợp đồng thành công.")
    except Exception:
        return redirect_with_flash("/contracts/", "Cập nhật hợp đồng thất bại.", "danger")

@router.post("/{contract_id}/delete")
async def delete_contract(request: Request, contract_id: str):
    db = get_db()
    if getattr(request.state, "user_role", None) not in ("admin", "manager"):
        return redirect_with_flash("/dashboard", "Bạn không có quyền xóa hợp đồng", "danger")
    try:
        await db.contracts.delete_one({"_id": ObjectId(contract_id)})
        await _refresh_room_statuses(db)
        return redirect_with_flash("/contracts/", "Xóa hợp đồng thành công.")
    except Exception:
        return redirect_with_flash("/contracts/", "Xóa hợp đồng thất bại.", "danger")

@router.post("/{contract_id}/end")
async def end_contract(
    request: Request, 
    contract_id: str,
    new_electric_index: int = Form(None) # Nhận thêm chỉ số điện mới từ Form
):
    db = get_db()
    if getattr(request.state, "user_role", None) not in ("admin", "manager"):
        return redirect_with_flash("/dashboard", "Bạn không có quyền kết thúc hợp đồng", "danger")
    
    import datetime as _dt
    today_dt = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=7)))
    today_iso = today_dt.date().isoformat()
    current_month = today_dt.strftime("%Y-%m")

    try:
        # 1. Tìm hợp đồng và phòng liên quan
        contract = await db.contracts.find_one({"_id": ObjectId(contract_id)})
        if not contract:
            return redirect_with_flash("/contracts/", "Không tìm thấy hợp đồng.", "danger")

        room_id = contract.get("room_id")
        room_oid = ObjectId(room_id) if len(str(room_id)) == 24 else None
        room = await db.rooms.find_one({"_id": room_oid}) if room_oid else await db.rooms.find_one({"room_number": room_id})
        
        if not room:
            return redirect_with_flash("/contracts/", "Không tìm thấy phòng liên kết.", "danger")

        # Lấy chỉ số điện cũ của phòng (dùng fallback tìm reading mới nhất nếu có)
        old_index = int(room.get("current_electric_index", 0))

        # 2. Kiểm tra chỉ số điện tháng hiện tại (so khớp nhiều dạng room_id)
        existing_reading = await db.electric_readings.find_one({
            "$and": [
                {"month": current_month},
                {"$or": [{"room_id": str(room.get("_id"))}, {"room_id": room.get("_id")}, {"room_id": str(room.get("room_number"))}, {"room_id": room.get("room_number")} ]}
            ]
        })

        # Nếu không có bản chốt cho tháng này, tìm bản ghi mới nhất để lấy prev_index chính xác
        last_reading = None
        if not existing_reading:
            candidates = []
            try:
                candidates.append(room.get("_id"))
            except Exception:
                pass
            try:
                candidates.append(str(room.get("_id")))
            except Exception:
                pass
            try:
                rn = room.get("room_number")
                if rn is not None:
                    candidates.append(rn)
                    candidates.append(str(rn))
            except Exception:
                pass
            or_clauses = [{"room_id": c} for c in candidates] if candidates else []
            if or_clauses:
                try:
                    last_reading = await db.electric_readings.find_one({"$or": or_clauses}, sort=[("month", -1), ("_id", -1)])
                except Exception:
                    last_reading = None

        used_kwh = 0
        prev_index = old_index
        curr_index = old_index

        if existing_reading:
            # Đã chốt điện tháng này, lấy số liệu đã chốt
            prev_index = int(existing_reading.get("old_index", old_index))
            curr_index = int(existing_reading.get("new_index", prev_index))
            used_kwh = max(0, curr_index - prev_index)
            # Đồng bộ lại chỉ số phòng nếu cần
            try:
                await db.rooms.update_one({"_id": room.get("_id")}, {"$set": {"current_electric_index": curr_index}})
            except Exception:
                pass
        else:
            # Chưa chốt điện tháng này -> sử dụng last_reading làm prev nếu có
            if last_reading:
                try:
                    prev_index = int(last_reading.get("new_index", old_index))
                except Exception:
                    prev_index = old_index
            else:
                prev_index = old_index

            if new_electric_index is None:
                # Trả về lỗi nếu Frontend không gửi số điện lên
                return redirect_with_flash("/contracts/", f"Phòng chưa có số điện tháng {current_month}. Vui lòng nhập số điện!", "warning")
            elif new_electric_index < prev_index:
                return redirect_with_flash("/contracts/", "Chỉ số mới không được nhỏ hơn chỉ số cũ.", "danger")
            else:
                # Ghi nhận chỉ số điện mới
                curr_index = new_electric_index
                used_kwh = curr_index - prev_index
                await db.electric_readings.insert_one({
                    "room_id": str(room.get("_id")),
                    "month": current_month,
                    "old_index": prev_index,
                    "new_index": curr_index,
                    "usage": used_kwh,
                    "price_per_kwh": constants.PRICE_PER_KWH,
                    "total": used_kwh * constants.PRICE_PER_KWH,
                    "created_at": today_dt
                })
                # Cập nhật số điện hiện tại của phòng
                await db.rooms.update_one({"_id": room.get("_id")}, {"$set": {"current_electric_index": curr_index}})

        # 3. Tạo hóa đơn thanh lý (dùng schema giống /bills/generate)
        electric_price = constants.PRICE_PER_KWH
        water_fee = constants.WATER_FEE
        electric_cost = used_kwh * electric_price
        total = electric_cost + water_fee

        bill_doc = {
            "contract_id": contract_id,
            "room_id": str(room.get("_id")),
            "tenant_id": contract.get("tenant_id"),
            "month": current_month,
            "room_price": 0,
            "electric_cost": electric_cost,
            "water_cost": water_fee,
            "other_cost": 0,
            "total": total,
            "status": "unpaid",
            "type": "liquidation",
            "created_at": datetime.datetime.utcnow(),
            "prev_index": prev_index,
            "curr_index": curr_index,
            "usage": used_kwh,
            "kwh_price": electric_price
        }
        # Nếu đã có hóa đơn cho hợp đồng này trong tháng hiện tại, cập nhật nó thay vì chèn mới
        try:
            existing_bill = await db.bills.find_one({"contract_id": contract_id, "month": current_month})
            if not existing_bill:
                existing_bill = await db.bills.find_one({"contract_id": str(contract.get("_id")), "month": current_month})
        except Exception:
            existing_bill = None

        if existing_bill:
            try:
                await db.bills.update_one({"_id": existing_bill.get("_id")}, {"$set": {
                    "room_price": 0,
                    "electric_cost": electric_cost,
                    "water_cost": water_fee,
                    "other_cost": 0,
                    "total": total,
                    "status": "unpaid",
                    "type": "liquidation",
                    "prev_index": prev_index,
                    "curr_index": curr_index,
                    "usage": used_kwh,
                    "kwh_price": electric_price
                }})
                print(f"[INFO] Updated existing liquidation bill for contract {contract_id}: electric_cost={electric_cost}, total={total}")
            except Exception as e:
                print(f"[WARN] Failed to update existing bill: {e}")
                await db.bills.insert_one(bill_doc)
        else:
            await db.bills.insert_one(bill_doc)
            print(f"[INFO] Inserted new liquidation bill for contract {contract_id}: electric_cost={electric_cost}, total={total}")

        # 4. Cập nhật trạng thái kết thúc hợp đồng
        # Lùi end_date về 1 ngày trước để hợp đồng MẤT HIỆU LỰC NGAY LẬP TỨC
        yesterday_iso = (today_dt - _dt.timedelta(days=1)).date().isoformat()
        
        await db.contracts.update_one(
            {"_id": ObjectId(contract_id)}, 
            {"$set": {
                "termination_date": today_iso, 
                "end_date": yesterday_iso  # <-- Quan trọng
            }}
        )
        
        # Làm mới trạng thái phòng (để phòng chuyển thành "Trống")
        await _refresh_room_statuses(db)

        # Cập nhật lại câu thông báo có cả Tiền Nước
        return redirect_with_flash(
            "/contracts/", 
            f"Thanh lý thành công! Đã tạo hóa đơn (Điện: {electric_cost:,.0f}đ, Nước: {water_fee:,.0f}đ).", 
            "success"
        )
    
    except Exception as e:
        print(f"Lỗi khi kết thúc hợp đồng: {e}")
        return redirect_with_flash("/contracts/", "Có lỗi xảy ra khi kết thúc hợp đồng.", "danger")