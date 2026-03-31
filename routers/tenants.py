from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from core.deps import get_db
from bson import ObjectId
import os
from jinja2 import Environment, FileSystemLoader

from core.security import decrypt_value, encrypt_value, hash_value, tenant_doc_to_ui
from core.flash import redirect_with_flash

router = APIRouter(prefix="/tenants", tags=["tenants"])

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


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


def _contract_order_key(contract_doc):
    import datetime
    try:
        d = datetime.date.fromisoformat(str(contract_doc.get("start_date")))
    except Exception:
        d = datetime.date.min
    return (d, str(contract_doc.get("_id")))


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


async def _refresh_tenant_statuses(db):
    latest_by_room = {}
    cursor = db.contracts.find({})
    async for c in cursor:
        rid_norm = await _normalize_room_id_to_oid_str(db, c.get("room_id"))
        if not rid_norm:
            continue
        current = latest_by_room.get(rid_norm)
        if (not current) or (_contract_order_key(c) > _contract_order_key(current)):
            latest_by_room[rid_norm] = c

    active_tenant_ids = set()
    for c in latest_by_room.values():
        tid = c.get("tenant_id")
        if not tid:
            continue
        try:
            ObjectId(str(tid))
            active_tenant_ids.add(str(tid))
        except Exception:
            pass

    tenants_cursor = db.tenants.find({})
    async for t in tenants_cursor:
        tid = str(t.get("_id"))
        new_status = "Đang thuê" if tid in active_tenant_ids else "Đã kết thúc"
        # Only backfill missing status for legacy records; allow manual editing in UI.
        if t.get("rental_status") is None:
            await db.tenants.update_one({"_id": t.get("_id")}, {"$set": {"rental_status": new_status}})


def _fix_id(doc):
    if not doc:
        return None
    doc["id"] = str(doc.get("_id"))
    return doc


# 1. API Trả về khung HTML trống (Cập nhật cho CSR)
@router.get("/")
async def list_tenants(request: Request, q: str = ""):
    db = get_db()
    await _refresh_tenant_statuses(db)
    tpl = env.get_template("tenants.html")
    html = tpl.render(request=request, q=q or "")
    return HTMLResponse(content=html)


# 2. API Trả về dữ liệu JSON (MỚI THÊM)
@router.get("/_list")
async def list_tenants_json(q: str = ""):
    db = get_db()
    await _refresh_tenant_statuses(db)
    query = {}
    if q:
        query = {"full_name": {"$regex": q, "$options": "i"}}
    cursor = db.tenants.find(query)
    tenants = []
    async for t in cursor:
        tenants.append(tenant_doc_to_ui(t))
    return tenants


@router.post("/create")
async def create_tenant(
    full_name: str = Form(...),
    cccd: str = Form(...),
    gender: str = Form(None),
    birth_year: int = Form(None),
    phone: str = Form(None),
    rental_status: str = Form("Đã kết thúc"),
):
    db = get_db()
    try:
        cccd_norm = str(cccd).strip()
        phone_norm = str(phone).strip() if phone is not None else None
        cccd_h = hash_value(cccd_norm)
        phone_h = hash_value(phone_norm) if phone_norm else None

        # Find by hash (new encrypted records). Fallback to legacy plaintext lookup.
        existing = None
        if cccd_h:
            existing = await db.tenants.find_one({"cccd_hash": cccd_h})
        if not existing:
            existing = await db.tenants.find_one({"cccd": cccd_norm})

        cccd_enc = encrypt_value(cccd_norm, require_key=True)
        phone_enc = encrypt_value(phone_norm, require_key=True) if phone_norm else None
        rental_status = rental_status if rental_status in ("Đang thuê", "Đã kết thúc") else "Đã kết thúc"

        if existing:
            await db.tenants.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "full_name": full_name,
                        "gender": gender,
                        "birth_year": birth_year,
                        "cccd": cccd_enc,
                        "cccd_hash": cccd_h,
                        "phone": phone_enc,
                        "phone_hash": phone_h,
                        "rental_status": rental_status,
                    }
                }
            )
        else:
            await db.tenants.insert_one(
                {
                    "full_name": full_name,
                    "cccd": cccd_enc,
                    "cccd_hash": cccd_h,
                    "gender": gender,
                    "birth_year": birth_year,
                    "phone": phone_enc,
                    "phone_hash": phone_h,
                    "rental_status": rental_status,
                }
            )
        return redirect_with_flash("/tenants/", "Lưu người thuê thành công.")
    except Exception:
        return redirect_with_flash("/tenants/", "Lưu người thuê thất bại.", "danger")


@router.post("/{tenant_id}/update")
async def update_tenant(
    tenant_id: str,
    full_name: str = Form(...),
    cccd: str = Form(...),
    gender: str = Form(None),
    birth_year: int = Form(None),
    phone: str = Form(None),
    rental_status: str = Form("Đã kết thúc"),
):
    db = get_db()
    try:
        cccd_norm = str(cccd).strip()
        phone_norm = str(phone).strip() if phone is not None else None
        cccd_h = hash_value(cccd_norm)
        phone_h = hash_value(phone_norm) if phone_norm else None

        cccd_enc = encrypt_value(cccd_norm, require_key=True)
        phone_enc = encrypt_value(phone_norm, require_key=True) if phone_norm else None
        rental_status = rental_status if rental_status in ("Đang thuê", "Đã kết thúc") else "Đã kết thúc"

        await db.tenants.update_one(
            {"_id": ObjectId(tenant_id)},
            {
                "$set": {
                    "full_name": full_name,
                    "gender": gender,
                    "birth_year": birth_year,
                    "cccd": cccd_enc,
                    "cccd_hash": cccd_h,
                    "phone": phone_enc,
                    "phone_hash": phone_h,
                    "rental_status": rental_status,
                }
            },
        )
        return redirect_with_flash("/tenants/", "Cập nhật người thuê thành công.")
    except Exception:
        return redirect_with_flash("/tenants/", "Cập nhật người thuê thất bại.", "danger")


@router.post("/{tenant_id}/delete")
async def delete_tenant(tenant_id: str):
    db = get_db()
    try:
        await db.tenants.delete_one({"_id": ObjectId(tenant_id)})
        return redirect_with_flash("/tenants/", "Xóa người thuê thành công.")
    except Exception:
        return redirect_with_flash("/tenants/", "Xóa người thuê thất bại.", "danger")


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str):
    db = get_db()
    doc = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
    if not doc:
        raise HTTPException(404)
    # Decrypt sensitive fields before returning to UI/JSON consumers.
    result = _fix_id(doc)
    result["phone"] = decrypt_value(doc.get("phone"))
    result["cccd"] = decrypt_value(doc.get("cccd"))
    # attach contracts and rooms for this tenant
    try:
        cursor = db.contracts.find({"tenant_id": str(doc.get("_id"))})
        contracts = []
        async for c in cursor:
            c["id"] = str(c.get("_id"))
            room_info = None
            try:
                room_id = c.get("room_id")
                try:
                    room_doc = await db.rooms.find_one({"_id": ObjectId(room_id)})
                except Exception:
                    room_doc = await _find_room_by_number(db, room_id)
                if room_doc:
                    room_doc["id"] = str(room_doc.get("_id"))
                    room_info = {"room_number": room_doc.get("room_number"), "id": room_doc.get("id"), "price": room_doc.get("price"), "status": room_doc.get("status")}
            except Exception:
                pass
            c_summary = {"id": c.get("id"), "room": room_info, "start_date": c.get("start_date"), "end_date": c.get("end_date"), "deposit": c.get("deposit")}
            contracts.append(c_summary)
        if contracts:
            result["contracts"] = contracts
    except Exception:
        pass
    return result