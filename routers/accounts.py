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


@router.get("/", response_class=HTMLResponse)
async def list_accounts(request: Request):
    db = get_db()
    cursor = db.accounts.find({})
    accts = []
    async for a in cursor:
        accts.append(_fix(a))
    tpl = env.get_template("accounts.html")
    html = tpl.render(request=request, accounts=accts, total=len(accts))
    return HTMLResponse(content=html)


@router.post("/create")
async def create_account(username: str = Form(...), password: str = Form(...), role: str = Form('manager')):
    db = get_db()
    try:
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
async def update_account(account_id: str, username: str = Form(...), role: str = Form(...), password: str = Form('')):
    db = get_db()
    try:
        update = {"username": username, "role": role}
        if password and str(password).strip():
            update['password'] = hash_password(password)
        await db.accounts.update_one({"_id": ObjectId(account_id)}, {"$set": update})
        return redirect_with_flash('/accounts/', 'Cập nhật tài khoản thành công')
    except Exception:
        return redirect_with_flash('/accounts/', 'Cập nhật thất bại', 'danger')


@router.post('/{account_id}/delete')
async def delete_account(account_id: str):
    db = get_db()
    try:
        await db.accounts.delete_one({"_id": ObjectId(account_id)})
        return redirect_with_flash('/accounts/', 'Xóa tài khoản thành công')
    except Exception:
        return redirect_with_flash('/accounts/', 'Xóa thất bại', 'danger')
