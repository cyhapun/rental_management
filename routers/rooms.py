from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from deps import get_db
from bson import ObjectId
import os
from jinja2 import Environment, FileSystemLoader

from security import decrypt_value
from template_filters import money
from flash import redirect_with_flash

router = APIRouter(prefix="/rooms", tags=["rooms"])

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
env.filters["money"] = money


def _fix_id(doc):
    if not doc:
        return None
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/", response_class=HTMLResponse)
async def list_rooms(request: Request, q: str = ""):
    db = get_db()
    query = {}
    if q:
        try:
            query = {"room_number": int(str(q).strip())}
        except Exception:
            query = {"room_number": -999999999}
    cursor = db.rooms.find(query)
    rooms = []
    async for r in cursor:
        # Normalize legacy room_number string -> int for consistent schema.
        room_num = r.get("room_number")
        if isinstance(room_num, str):
            try:
                parsed_room_num = int(room_num.strip())
                await db.rooms.update_one({"_id": r.get("_id")}, {"$set": {"room_number": parsed_room_num}})
                r["room_number"] = parsed_room_num
            except Exception:
                pass
        # Keep backward compatibility for old rooms without this field.
        r["current_electric_index"] = r.get("current_electric_index", 0)
        # build JSON-serializable copy: convert Mongo _id to string id and drop raw _id
        serializable = dict(r)
        if serializable.get("_id") is not None:
            try:
                serializable["id"] = str(serializable.get("_id"))
            except Exception:
                serializable["id"] = None
            serializable.pop("_id", None)
        rooms.append(serializable)
    tpl = env.get_template("rooms.html")
    html = tpl.render(request=request, rooms=rooms, q=q or "")
    return HTMLResponse(content=html)


@router.get("/_list")
async def list_rooms_json(q: str = ""):
    db = get_db()
    query = {}
    if q:
        try:
            query = {"room_number": int(str(q).strip())}
        except Exception:
            query = {"room_number": -999999999}
    cursor = db.rooms.find(query)
    rooms = []
    async for r in cursor:
        # Normalize legacy room_number string -> int for consistent schema.
        room_num = r.get("room_number")
        if isinstance(room_num, str):
            try:
                parsed_room_num = int(room_num.strip())
                await db.rooms.update_one({"_id": r.get("_id")}, {"$set": {"room_number": parsed_room_num}})
                r["room_number"] = parsed_room_num
            except Exception:
                pass
        r["current_electric_index"] = r.get("current_electric_index", 0)
        rooms.append(_fix_id(r))
    return rooms


@router.post("/create")
async def create_room(room_number: int = Form(...), price: int = Form(...), current_electric_index: int = Form(0)):
    db = get_db()
    try:
        room_number = int(room_number)
        existing = await db.rooms.find_one({"room_number": room_number})
        if existing:
            return redirect_with_flash("/rooms/", "Phòng đã tồn tại.", "danger")
        await db.rooms.insert_one(
            {
                "room_number": room_number,
                "price": price,
                "status": "available",
                "current_electric_index": max(0, int(current_electric_index)),
            }
        )
        return redirect_with_flash("/rooms/", "Thêm phòng thành công.")
    except Exception:
        return redirect_with_flash("/rooms/", "Thêm phòng thất bại.", "danger")


@router.post("/{room_id}/update")
async def update_room(
    room_id: str,
    room_number: int = Form(...),
    price: int = Form(...),
    status: str = Form("available"),
    current_electric_index: int = Form(0),
):
    db = get_db()
    try:
        room_number = int(room_number)
        await db.rooms.update_one(
            {"_id": ObjectId(room_id)},
            {
                "$set": {
                    "room_number": room_number,
                    "price": price,
                    "status": status,
                    "current_electric_index": max(0, int(current_electric_index)),
                }
            },
        )
        return redirect_with_flash("/rooms/", "Cập nhật phòng thành công.")
    except Exception:
        return redirect_with_flash("/rooms/", "Cập nhật phòng thất bại.", "danger")


@router.get("/{room_id}")
async def get_room(room_id: str):
    db = get_db()
    doc = await db.rooms.find_one({"_id": ObjectId(room_id)})
    if not doc:
        raise HTTPException(404)
    result = _fix_id(doc)
    # attach current contract and tenant if exists
    try:
        # contracts may store room_id as string of ObjectId
        contract = await db.contracts.find_one({"room_id": str(doc.get("_id"))})
        if contract:
            contract["id"] = str(contract.get("_id"))
            tenant = None
            try:
                tenant_id = contract.get("tenant_id")
                if tenant_id:
                    tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
            except Exception:
                tenant = None
            if tenant:
                tenant["id"] = str(tenant.get("_id"))
                result["current_contract"] = {
                    "contract_id": contract.get("id"),
                    "tenant": {"id": tenant.get("id"), "full_name": tenant.get("full_name"), "phone": decrypt_value(tenant.get("phone"))},
                    "start_date": contract.get("start_date"),
                    "end_date": contract.get("end_date"),
                }
    except Exception:
        pass
    return result


@router.post("/{room_id}/delete")
async def delete_room(room_id: str):
    db = get_db()
    try:
        await db.rooms.delete_one({"_id": ObjectId(room_id)})
        return redirect_with_flash("/rooms/", "Xóa phòng thành công.")
    except Exception:
        return redirect_with_flash("/rooms/", "Xóa phòng thất bại.", "danger")
