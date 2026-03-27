from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from app.deps import get_db
from bson import ObjectId
import datetime
import os
from jinja2 import Environment, FileSystemLoader

from app.security import decrypt_value, mask_cccd
from app.template_filters import money
from app.security import hash_value
from app.flash import redirect_with_flash

router = APIRouter(prefix="/contracts", tags=["contracts"])

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.filters["money"] = money


def _is_active_contract(contract_doc: dict, today: datetime.date) -> bool:
    end = contract_doc.get("end_date")
    if not end:
        return True
    try:
        end_date = datetime.date.fromisoformat(str(end))
    except Exception:
        return True
    return end_date >= today


def _contract_order_key(contract_doc: dict):
    """
    Dùng để chọn hợp đồng mới nhất của 1 phòng.
    Ưu tiên start_date, fallback theo _id.
    """
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
    # Try current month due date first
    while True:
        try:
            candidate = datetime.date(year, month, day)
        except ValueError:
            # Handle months without this day (e.g. 31)
            # use last day of month
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
        room_doc = await db.rooms.find_one({"room_number": rid_str})
        if room_doc:
            return str(room_doc.get("_id"))
    return None


async def _refresh_room_statuses(db):
    """
    Đồng bộ trạng thái phòng theo hợp đồng còn hiệu lực.
    """
    latest_by_room = {}
    cursor = db.contracts.find({})
    async for c in cursor:
        rid_norm = await _normalize_room_id_to_oid_str(db, c.get("room_id"))
        if not rid_norm:
            continue
        current = latest_by_room.get(rid_norm)
        if (not current) or (_contract_order_key(c) > _contract_order_key(current)):
            latest_by_room[rid_norm] = c
    occupied_room_ids = set(latest_by_room.keys())

    # Cập nhật tất cả phòng theo trạng thái đã tính
    rooms_cursor = db.rooms.find({})
    async for r in rooms_cursor:
        rid = str(r.get("_id"))
        new_status = "occupied" if rid in occupied_room_ids else "available"
        if r.get("status") != new_status:
            await db.rooms.update_one({"_id": r.get("_id")}, {"$set": {"status": new_status}})


async def _normalize_contract_refs(db):
    """
    Chuẩn hóa dữ liệu legacy trong contracts:
    - room_id: ObjectId -> str(ObjectId), room_number -> lookup rooms._id
    - tenant_id: ObjectId -> str(ObjectId), CCCD -> lookup tenants by cccd_hash/plain cccd
    """
    cursor = db.contracts.find({})
    async for c in cursor:
        updates = {}

        # room_id normalization
        rid = c.get("room_id")
        if rid is not None:
            if isinstance(rid, ObjectId):
                updates["room_id"] = str(rid)
            else:
                rid_str = str(rid)
                try:
                    ObjectId(rid_str)
                    # already looks like ObjectId string
                    updates["room_id"] = rid_str
                except Exception:
                    # treat as room_number
                    room_doc = await db.rooms.find_one({"room_number": rid_str})
                    if room_doc:
                        updates["room_id"] = str(room_doc.get("_id"))

        # tenant_id normalization
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
                    # best effort: treat as CCCD
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


@router.get("/")
async def list_contracts(request: Request):
    db = get_db()
    await _normalize_contract_refs(db)
    await _refresh_room_statuses(db)
    cursor = db.contracts.find({})
    contracts = []
    active_room_ids = set()
    active_tenant_ids = set()
    today = datetime.date.today()
    latest_by_room = {}
    all_contracts = []
    async for c in cursor:
        all_contracts.append(c)
        rid_norm = await _normalize_room_id_to_oid_str(db, c.get("room_id"))
        if rid_norm:
            current = latest_by_room.get(rid_norm)
            if (not current) or (_contract_order_key(c) > _contract_order_key(current)):
                latest_by_room[rid_norm] = c

    latest_contract_ids = {str(v.get("_id")) for v in latest_by_room.values()}

    for c in all_contracts:
        c["id"] = str(c.get("_id"))
        # "Hợp đồng hiện hành" theo nghiệp vụ thao tác: mới nhất theo phòng
        c["is_active"] = c["id"] in latest_contract_ids
        if c["is_active"]:
            rid_norm = await _normalize_room_id_to_oid_str(db, c.get("room_id"))
            if rid_norm:
                active_room_ids.add(rid_norm)

            # tenant normalization (handle ObjectId vs other legacy formats)
            if c.get("tenant_id"):
                tid_str = str(c.get("tenant_id"))
                try:
                    ObjectId(tid_str)
                    active_tenant_ids.add(tid_str)
                except Exception:
                    # legacy might store CCCD (encrypted/plain). Best effort: ignore.
                    pass
        # attach tenant and room info when available
        try:
            tenant_id = c.get("tenant_id")
            if tenant_id:
                tenant_doc = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
                if tenant_doc:
                    tenant_doc["id"] = str(tenant_doc.get("_id"))
                    c["tenant"] = {
                        "full_name": tenant_doc.get("full_name"),
                        "phone": decrypt_value(tenant_doc.get("phone")),
                        "id": tenant_doc.get("id"),
                        "cccd": mask_cccd(decrypt_value(tenant_doc.get("cccd"))),
                    }
        except Exception:
            pass
        try:
            room_id = c.get("room_id")
            if room_id:
                # room_id may be stored as string; try to fetch by ObjectId or by room_number
                room_doc = None
                try:
                    room_doc = await db.rooms.find_one({"_id": ObjectId(room_id)})
                except Exception:
                    room_doc = await db.rooms.find_one({"room_number": room_id})
                if room_doc:
                    room_doc["id"] = str(room_doc.get("_id"))
                    c["room"] = {"room_number": room_doc.get("room_number"), "price": room_doc.get("price"), "status": room_doc.get("status"), "id": room_doc.get("id")}
        except Exception:
            pass
        # latest electric reading for this contract's room
        try:
            latest_er = await db.electric_readings.find_one(
                {"room_id": c.get("room_id")},
                sort=[("month", -1), ("_id", -1)],
            )
            if latest_er:
                current_kwh = int(latest_er.get("new_index", 0))
                used_kwh = int(latest_er.get("new_index", 0)) - int(latest_er.get("old_index", 0))
                c["electric"] = {
                    "current_kwh": current_kwh,
                    "used_kwh": used_kwh,
                    "month": latest_er.get("month"),
                }
            else:
                c["electric"] = {"current_kwh": 0, "used_kwh": 0, "month": None}
        except Exception:
            c["electric"] = {"current_kwh": 0, "used_kwh": 0, "month": None}

        # payment status of latest room bill for this contract
        try:
            latest_bill = await db.bills.find_one(
                {"contract_id": c.get("id")},
                sort=[("month", -1), ("created_at", -1), ("_id", -1)],
            )
            if latest_bill:
                c["rent_payment_status"] = latest_bill.get("status", "unpaid")
                c["rent_payment_month"] = latest_bill.get("month")
            else:
                c["rent_payment_status"] = "no_bill"
                c["rent_payment_month"] = None
        except Exception:
            c["rent_payment_status"] = "unknown"
            c["rent_payment_month"] = None
        contracts.append(c)
    # data for create-contract dropdowns
    tenants = []
    async for t in db.tenants.find({}).sort("full_name", 1):
        t["id"] = str(t.get("_id"))
        tenants.append(
            {
                "id": t.get("id"),
                "full_name": t.get("full_name"),
                "phone": decrypt_value(t.get("phone")),
                "cccd": mask_cccd(decrypt_value(t.get("cccd"))),
            }
        )
    rooms = []
    async for r in db.rooms.find({}).sort("room_number", 1):
        r["id"] = str(r.get("_id"))
        rooms.append({"id": r.get("id"), "room_number": r.get("room_number"), "price": r.get("price"), "status": r.get("status")})
    warnings = []
    today_str = today.isoformat()
    for c in contracts:
        if not c.get("is_active"):
            continue
        start = c.get("start_date")
        try:
            start_date = datetime.date.fromisoformat(str(start))
        except Exception:
            continue
        due = _next_due_date(start_date, today)
        days_left = (due - today).days
        if days_left == 1:
            warnings.append(
                {
                    "room_number": c.get("room", {}).get("room_number") if c.get("room") else c.get("room_id"),
                    "tenant_name": c.get("tenant", {}).get("full_name") if c.get("tenant") else c.get("tenant_id"),
                    "due_date": due.isoformat(),
                }
            )
    tpl = env.get_template("contracts.html")
    html = tpl.render(
        request=request,
        contracts=contracts,
        warnings=warnings,
        tenants=tenants,
        rooms=rooms,
        active_room_ids=list(active_room_ids),
        active_tenant_ids=list(active_tenant_ids),
        today=today_str,
    )
    return HTMLResponse(content=html)


@router.post("/create")
async def create_contract(tenant_id: str = Form(...), room_id: str = Form(...), start_date: str = Form(...), end_date: str = Form(None), contract_type: str = Form(None), deposit: int = Form(0)):
    db = get_db()
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
    contract_id: str,
    tenant_id: str = Form(...),
    room_id: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(None),
    contract_type: str = Form(None),
    deposit: int = Form(0),
):
    db = get_db()
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
async def delete_contract(contract_id: str):
    db = get_db()
    try:
        await db.contracts.delete_one({"_id": ObjectId(contract_id)})
        await _refresh_room_statuses(db)
        return redirect_with_flash("/contracts/", "Xóa hợp đồng thành công.")
    except Exception:
        return redirect_with_flash("/contracts/", "Xóa hợp đồng thất bại.", "danger")
