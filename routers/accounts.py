from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from deps import get_db
from bson import ObjectId
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from security import hash_password
from flash import redirect_with_flash

router = APIRouter(prefix="/accounts", tags=["accounts"])

TEMPLATES_DIR = __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', 'templates'))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def _fix(doc):
    if not doc:
        return None
    created = doc.get("created_at")
    if isinstance(created, datetime):
        created_str = created.strftime("%Y-%m-%d %H:%M")
    else:
        created_str = str(created) if created is not None else ''
    return {"id": str(doc.get("_id")), "username": doc.get("username"), "role": doc.get("role", "manager"), "created_at": created_str}


# 1. API Trả về khung HTML siêu nhẹ
@router.get("/", response_class=HTMLResponse)
async def list_accounts(request: Request):
    tpl = env.get_template("accounts.html")
    # KHÔNG truy vấn database và truyền 'accounts' ở đây nữa
    html = tpl.render(request=request)
    return HTMLResponse(content=html)


# 2. API Trả về dữ liệu JSON (để Javascript gọi ngầm)
@router.get("/_data")
async def get_accounts_data(request: Request):
    db = get_db()
    # Nếu muốn bảo mật hơn, có thể check quyền admin tại đây:
    # if getattr(request.state, 'user_role', None) != 'admin':
    #     return {"accounts": [], "total": 0}
        
    cursor = db.accounts.find({})
    accts = []
    async for a in cursor:
        accts.append(_fix(a))
    
    return {"accounts": accts, "total": len(accts)}


@router.post("/create")
async def create_account(request: Request, username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), role: str = Form('manager')):
    db = get_db()
    if getattr(request.state, 'user_role', None) != 'admin':
        return redirect_with_flash('/dashboard', 'Bạn không có quyền để tạo tài khoản', 'danger')
    try:
        if password != confirm_password:
            return redirect_with_flash('/accounts/', 'Mật khẩu và xác nhận mật khẩu không khớp', 'danger')
        existing = await db.accounts.find_one({"username": username})
        if existing:
            return redirect_with_flash('/accounts/', 'Tên đăng nhập đã tồn tại', 'danger')
        pw = hash_password(password)
        doc = {"username": username, "password": pw, "role": role, "created_at": datetime.utcnow()}
        await db.accounts.insert_one(doc)
        return redirect_with_flash('/accounts/', 'Tạo tài khoản thành công')
    except Exception:
        return redirect_with_flash('/accounts/', 'Tạo tài khoản thất bại', 'danger')


@router.post('/{account_id}/update')
async def update_account(request: Request, account_id: str, username: str = Form(...), role: str = Form(...), password: str = Form('')):
    db = get_db()
    if getattr(request.state, 'user_role', None) != 'admin':
        return redirect_with_flash('/dashboard', 'Bạn không có quyền để cập nhật tài khoản', 'danger')
    try:
        update = {"username": username, "role": role}
        if password and str(password).strip():
            update['password'] = hash_password(password)
        await db.accounts.update_one({"_id": ObjectId(account_id)}, {"$set": update})
        return redirect_with_flash('/accounts/', 'Cập nhật tài khoản thành công')
    except Exception:
        return redirect_with_flash('/accounts/', 'Cập nhật thất bại', 'danger')


@router.post('/{account_id}/delete')
async def delete_account(request: Request, account_id: str):
    db = get_db()
    if getattr(request.state, 'user_role', None) != 'admin':
        return redirect_with_flash('/dashboard', 'Bạn không có quyền để xóa tài khoản', 'danger')
    try:
        await db.accounts.delete_one({"_id": ObjectId(account_id)})
        return redirect_with_flash('/accounts/', 'Xóa tài khoản thành công')
    except Exception:
        return redirect_with_flash('/accounts/', 'Xóa thất bại', 'danger')