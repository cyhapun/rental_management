from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from core.deps import get_db
from bson import ObjectId
import os
import datetime
from jinja2 import Environment, FileSystemLoader

from core.security import decrypt_value, mask_cccd
from core.flash import redirect_with_flash

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

# 1. API Trả về khung HTML siêu nhẹ
@router.get("/")
async def list_electric(request: Request):
    db = get_db()
    
    # Chỉ lấy danh sách phòng để đổ vào Dropdown Modal Thêm
    rooms = []
    async for r in db.rooms.find({}).sort("room_number", 1):
        rooms.append({
            "id": str(r.get("_id")), 
            "room_number": r.get("room_number"), 
            "status": r.get("status")
        })
        
    import datetime
    default_month = datetime.date.today().strftime("%Y-%m")
    
    tpl = env.get_template("electric.html")
    # KHÔNG TRUYỀN readings VÀO NỮA
    html = tpl.render(request=request, rooms=rooms, default_month=default_month)
    return HTMLResponse(content=html)


# 2. API Trả về dữ liệu JSON (Javascript sẽ gọi ngầm cái này)
@router.get("/_data")
async def get_electric_data():
    db = get_db()
    readings = []
    last_indices = {}
    
    # Lấy chỉ số mặc định của phòng làm dự phòng
    async for room in db.rooms.find({}):
        last_indices[str(room.get("_id"))] = room.get("current_electric_index", 0)

    # Lấy toàn bộ lịch sử điện năng
    cursor = db.electric_readings.find({}).sort([("month", -1), ("_id", -1)])
    
    seen_rooms_for_index = set()
    async for r in cursor:
        rid = str(r.get("_id"))
        room_id = str(r.get("room_id")) if r.get("room_id") else ""
        
        # Cập nhật số liệu điện mới nhất cho từng phòng (dành cho modal Thêm)
        if room_id and room_id not in seen_rooms_for_index:
            last_indices[room_id] = r.get("new_index", 0)
            seen_rooms_for_index.add(room_id)
        
        # Ánh xạ tên phòng
        room_doc = await db.rooms.find_one({"_id": ObjectId(room_id)}) if room_id else None
        room_number = room_doc.get("room_number") if room_doc else room_id
        
        readings.append({
            "id": rid,
            "room_id": room_id,
            "room": {"room_number": room_number},
            "month": r.get("month", ""),
            "old_index": r.get("old_index", 0),
            "new_index": r.get("new_index", 0),
            "usage": r.get("usage", 0),
            "price_per_kwh": r.get("price_per_kwh", 3000)
        })
        
    return {"readings": readings, "last_indices": last_indices}

@router.post("/add")
async def add_electric(
    request: Request,
    room_id: str = Form(...),
    month: str = Form(...),
    old_index: int = Form(0),
    new_index: int = Form(0),
    price_per_kwh: int = Form(3000)
):
    db = get_db()
    
    # 1. Tính toán lượng tiêu thụ
    usage = new_index - old_index
    if usage < 0:
        # Bạn có thể dùng flash message để báo lỗi nếu số mới thấp hơn số cũ
        return redirect_with_flash(request, "/electric", "Số mới không được nhỏ hơn số cũ!", "danger")

    # 2. Tạo bản ghi mới
    new_reading = {
        "room_id": room_id,
        "month": month,
        "old_index": old_index,
        "new_index": new_index,
        "usage": usage,
        "price_per_kwh": price_per_kwh,
        "created_at": datetime.datetime.now()
    }
    
    await db.electric_readings.insert_one(new_reading)
    
    # 3. Cập nhật lại chỉ số hiện tại của phòng (Sử dụng hàm helper có sẵn của bạn)
    await _sync_room_current_index(db, room_id)
    
    return RedirectResponse(url="/electric", status_code=303)


@router.post("/{reading_id}/update")
async def update_electric(
    request: Request,
    reading_id: str,
    month: str = Form(...),
    old_index: int = Form(...),
    new_index: int = Form(...),
    price_per_kwh: int = Form(...)
):
    db = get_db()
    usage = new_index - old_index
    
    if usage < 0:
        return redirect_with_flash(request, "/electric", "Lỗi: Số mới không được nhỏ hơn số cũ!", "danger")

    # Tìm bản ghi cũ để biết room_id (phục vụ việc sync sau khi update)
    old_doc = await db.electric_readings.find_one({"_id": ObjectId(reading_id)})
    if not old_doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi")

    await db.electric_readings.update_one(
        {"_id": ObjectId(reading_id)},
        {"$set": {
            "month": month,
            "old_index": old_index,
            "new_index": new_index,
            "usage": usage,
            "price_per_kwh": price_per_kwh
        }}
    )
    
    # Đồng bộ lại chỉ số phòng
    await _sync_room_current_index(db, old_doc.get("room_id"))
    
    return redirect_with_flash(request, "/electric", "Đã cập nhật chỉ số thành công.", "success")


@router.post("/{reading_id}/delete")
async def delete_electric(request: Request, reading_id: str):
    db = get_db()
    
    # Lấy thông tin bản ghi trước khi xóa để lấy room_id
    doc = await db.electric_readings.find_one({"_id": ObjectId(reading_id)})
    if doc:
        room_id = doc.get("room_id")
        await db.electric_readings.delete_one({"_id": ObjectId(reading_id)})
        # Sau khi xóa, số hiện tại của phòng phải lùi về bản ghi trước đó
        await _sync_room_current_index(db, room_id)
        
    return redirect_with_flash(request, "/electric", "Đã xóa bản ghi thành công.", "success")


@router.get("/last/{room_id}")
async def get_last_index(room_id: str):
    db = get_db()
    
    # Tìm bản ghi có tháng mới nhất của phòng này
    latest = await db.electric_readings.find_one(
        {"room_id": room_id},
        sort=[("month", -1), ("_id", -1)]
    )
    
    # Nếu chưa từng có bản ghi nào, lấy số mặc định từ bảng rooms
    if not latest:
        room = await db.rooms.find_one({"_id": ObjectId(room_id)})
        return {"old_index": room.get("current_electric_index", 0) if room else 0}
        
    return {"old_index": latest.get("new_index", 0)}