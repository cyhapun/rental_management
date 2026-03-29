from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from deps import get_db
from bson import ObjectId
import os
import datetime
from jinja2 import Environment, FileSystemLoader

from security import decrypt_value, mask_cccd
from flash import redirect_with_flash

router = APIRouter(prefix="/electric", tags=["electric"])

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


async def _sync_room_current_index(db, room_id_value: str):
    room_doc = None
    try:
        room_doc = await db.rooms.find_one({"_id": ObjectId(room_id_value)})
    except Exception:
        room_doc = await _find_room_by_number(db, room_id_value)
    if not room_doc:
        return

    room_oid_str = str(room_doc.get("_id"))
    room_number = str(room_doc.get("room_number"))
    latest = await db.electric_readings.find_one(
        {"$or": [{"room_id": room_oid_str}, {"room_id": room_number}]},
        sort=[("month", -1), ("_id", -1)],
    )
    try:
        current_idx = int((latest or {}).get("new_index", 0))
    except Exception:
        current_idx = 0
    await db.rooms.update_one({"_id": room_doc.get("_id")}, {"$set": {"current_electric_index": current_idx}})


@router.get("/")
async def list_readings(request: Request):
    db = get_db()
    cursor = db.electric_readings.find({}).sort("month", -1)
    readings = []
    async for r in cursor:
        r["id"] = str(r.get("_id"))
        # attach room info
        try:
            room_id = r.get("room_id")
            room_doc = None
            try:
                room_doc = await db.rooms.find_one({"_id": ObjectId(room_id)})
            except Exception:
                room_doc = await _find_room_by_number(db, room_id)
            if room_doc:
                room_doc["id"] = str(room_doc.get("_id"))
                r["room"] = {
                    "room_number": room_doc.get("room_number"),
                    "price": room_doc.get("price"),
                    "status": room_doc.get("status"),
                    "id": room_doc.get("id"),
                }
                # try to find active contract for this room to get tenant
                try:
                    contract = await db.contracts.find_one({"room_id": str(room_doc.get("_id"))})
                    if contract:
                        tenant_id = contract.get("tenant_id")
                        if tenant_id:
                            tenant_doc = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
                            if tenant_doc:
                                tenant_doc["id"] = str(tenant_doc.get("_id"))
                                r["tenant"] = {
                                    "full_name": tenant_doc.get("full_name"),
                                    "phone": decrypt_value(tenant_doc.get("phone")),
                                    "id": tenant_doc.get("id"),
                                    "cccd": mask_cccd(decrypt_value(tenant_doc.get("cccd"))),
                                }
                except Exception:
                    pass
        except Exception:
            pass
        readings.append(r)

    # rooms for dropdown
    rooms = []
    async for room in db.rooms.find({}).sort("room_number", 1):
        room["id"] = str(room.get("_id"))
        rooms.append(
            {
                "id": room.get("id"),
                "room_number": room.get("room_number"),
                "status": room.get("status"),
            }
        )

    # default month string YYYY-MM
    today = datetime.date.today()
    default_month = today.strftime("%Y-%m")

    tpl = env.get_template("electric.html")
    html = tpl.render(request=request, readings=readings, rooms=rooms, default_month=default_month)
    return HTMLResponse(content=html)


@router.post("/add")
async def add_reading(request: Request, room_id: str = Form(...), month: str = Form(...), old_index: int = Form(0), new_index: int = Form(...), price_per_kwh: float = Form(2000.0)):
    try:
        if getattr(request.state, "user_role", None) not in ("admin", "manager"):
            return redirect_with_flash("/dashboard", "Bạn không có quyền thêm chỉ số điện", "danger")
        usage = int(new_index) - int(old_index)
        total = int(usage * price_per_kwh)
        db = get_db()
        res = await db.electric_readings.insert_one(
            {
                "room_id": room_id,
                "month": month,
                "old_index": old_index,
                "new_index": new_index,
                "usage": usage,
                "price_per_kwh": price_per_kwh,
                "total": total,
            }
        )
        # record history
        try:
            await db.electric_history.insert_one({
                "action": "create",
                "reading_id": str(res.inserted_id) if res and getattr(res, 'inserted_id', None) else None,
                "room_id": room_id,
                "month": month,
                "old_index": old_index,
                "new_index": new_index,
                "usage": usage,
                "price_per_kwh": price_per_kwh,
                "total": total,
                "changed_by": getattr(request.state, 'user_id', None) or getattr(request.state, 'user', None),
                "changed_at": datetime.datetime.utcnow(),
            })
        except Exception:
            pass
        await _sync_room_current_index(db, room_id)
        return redirect_with_flash("/electric/", "Thêm chỉ số điện thành công.")
    except Exception:
        return redirect_with_flash("/electric/", "Thêm chỉ số điện thất bại.", "danger")


@router.post("/{reading_id}/update")
async def update_reading(
    request: Request,
    reading_id: str,
    month: str = Form(...),
    old_index: int = Form(0),
    new_index: int = Form(...),
    price_per_kwh: float = Form(2000.0),
):
    try:
        if getattr(request.state, "user_role", None) not in ("admin", "manager"):
            return redirect_with_flash("/dashboard", "Bạn không có quyền cập nhật chỉ số điện", "danger")
        db = get_db()
        doc = await db.electric_readings.find_one({"_id": ObjectId(reading_id)})
        if not doc:
            return redirect_with_flash("/electric/", "Không tìm thấy chỉ số điện.", "danger")
        usage = int(new_index) - int(old_index)
        total = int(usage * float(price_per_kwh))
        # update and record history (old values in doc)
        try:
            await db.electric_readings.update_one(
                {"_id": ObjectId(reading_id)},
                {
                    "$set": {
                        "month": month,
                        "old_index": old_index,
                        "new_index": new_index,
                        "usage": usage,
                        "price_per_kwh": price_per_kwh,
                        "total": total,
                    }
                },
            )
            try:
                await db.electric_history.insert_one({
                    "action": "update",
                    "reading_id": str(reading_id),
                    "room_id": doc.get("room_id"),
                    "month": month,
                    "old_index": doc.get("old_index"),
                    "new_index": new_index,
                    "old_usage": doc.get("usage"),
                    "new_usage": usage,
                    "old_price_per_kwh": doc.get("price_per_kwh"),
                    "new_price_per_kwh": price_per_kwh,
                    "old_total": doc.get("total"),
                    "new_total": total,
                    "changed_by": getattr(request.state, 'user_id', None) or getattr(request.state, 'user', None),
                    "changed_at": datetime.datetime.utcnow(),
                })
            except Exception:
                pass
        except Exception:
            pass
        await _sync_room_current_index(db, str(doc.get("room_id")))
        return redirect_with_flash("/electric/", "Cập nhật chỉ số điện thành công.")
    except Exception:
        return redirect_with_flash("/electric/", "Cập nhật chỉ số điện thất bại.", "danger")


@router.post("/{reading_id}/delete")
async def delete_reading(request: Request, reading_id: str):
    db = get_db()
    try:
        if getattr(request.state, "user_role", None) not in ("admin", "manager"):
            return redirect_with_flash("/dashboard", "Bạn không có quyền xóa chỉ số điện", "danger")
        doc = await db.electric_readings.find_one({"_id": ObjectId(reading_id)})
        # record deletion history
        try:
            if doc:
                await db.electric_history.insert_one({
                    "action": "delete",
                    "reading_id": str(reading_id),
                    "room_id": doc.get("room_id"),
                    "month": doc.get("month"),
                    "old_index": doc.get("old_index"),
                    "new_index": doc.get("new_index"),
                    "usage": doc.get("usage"),
                    "price_per_kwh": doc.get("price_per_kwh"),
                    "total": doc.get("total"),
                    "changed_by": getattr(request.state, 'user_id', None) or getattr(request.state, 'user', None),
                    "changed_at": datetime.datetime.utcnow(),
                })
        except Exception:
            pass
        await db.electric_readings.delete_one({"_id": ObjectId(reading_id)})
        if doc and doc.get("room_id"):
            await _sync_room_current_index(db, str(doc.get("room_id")))
        return redirect_with_flash("/electric/", "Xóa chỉ số điện thành công.")
    except Exception:
        return redirect_with_flash("/electric/", "Xóa chỉ số điện thất bại.", "danger")


@router.get("/last/{room_id}")
async def last_reading(room_id: str):
    """
    Trả về chỉ số điện cũ (old_index) cho phòng: lấy new_index mới nhất làm old_index.
    Dùng cho form nhập chỉ số điện để tự động điền.
    """
    db = get_db()
    # readings lưu room_id có thể là string ObjectId hoặc số phòng, nhưng form của mình truyền _id string.
    doc = await db.electric_readings.find_one({"room_id": room_id}, sort=[("month", -1)])
    if not doc:
        return JSONResponse({"old_index": 0})
    try:
        old_index = int(doc.get("new_index", 0))
    except Exception:
        old_index = 0
    return JSONResponse({"old_index": old_index})
