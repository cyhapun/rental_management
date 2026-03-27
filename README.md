# Quan Ly Nha Tro - FastAPI + MongoDB

He thong quan ly nha tro xay dung bang **FastAPI**, **MongoDB**, **Jinja2** va **Bootstrap 5**.
Ung dung ho tro quan ly phong, nguoi thue, hop dong, chi so dien, hoa don va in hoa don PDF.

## 1) Tinh nang chinh

- Quan ly phong, nguoi thue, hop dong, chi so dien, hoa don (CRUD day du).
- Lien ket du lieu bang ID de dam bao nhat quan (room/tenant/contract/bill).
- Ma hoa du lieu nhay cam (CCCD, so dien thoai) truoc khi luu DB.
- Loc, sap xep, tim kiem tren cac bang du lieu.
- Dashboard co bieu do tong quan (doanh thu, ty le phong, hoa don, tieu thu dien).
- In hoa don PDF ho tro tieng Viet.
- Thong bao dang toast tu dong an.
- Phan quyen dang nhap:
  - **Admin**: xem/chinh sua/cau hinh du lieu.
  - **Guest**: chi xem outline dashboard, khong duoc truy cap du lieu chi tiet.

## 2) Cong nghe su dung

- **Backend**: FastAPI, Uvicorn
- **Database**: MongoDB (Motor async driver)
- **Template/UI**: Jinja2, Bootstrap 5, Chart.js
- **Bao mat du lieu**: cryptography (Fernet), SHA256
- **PDF**: ReportLab
- **Cau hinh**: python-dotenv

## 3) Cau truc thu muc (rut gon)

```text
app/
  main.py
  deps.py
  security.py
  constants.py
  flash.py
  template_filters.py
  routers/
    auth.py
    dashboard.py
    rooms.py
    tenants.py
    contracts.py
    electric.py
    bills.py
    invoice.py
  templates/
  static/
  requirements.txt
  .env
```

## 4) Cai dat va chay local

### 4.1 Tao moi truong ao + cai thu vien

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Sau do cai packages:

```bash
pip install -r requirements.txt
```

### 4.2 Cau hinh bien moi truong (`.env`)

Tao file `app/.env` voi noi dung mau:

```env
MONGO_URI=mongodb+srv://<user>:<password>@<cluster-url>/?retryWrites=true&w=majority
MONGO_DB=nha_tro

DATA_ENCRYPTION_KEY=<fernet_key>
WATER_FEE=50000

ADMIN_USER=admin
ADMIN_PASS=your_strong_password

GUEST_USER=guest
GUEST_PASS=guest
```

> Ghi chu: `DATA_ENCRYPTION_KEY` phai la Fernet key hop le.

### 4.3 Chay ung dung

```bash
uvicorn app.main:app --reload --port 8000
```

Mo trinh duyet:
- `http://localhost:8000`
- He thong se dieu huong den `/dashboard` hoac `/login` tuy theo trang thai dang nhap.

## 5) Phan quyen va bao mat

Ung dung su dung middleware xac thuc toan cuc:

- Chua dang nhap: bi redirect ve `/login`.
- Dang nhap role `guest`:
  - Co the vao dashboard o che do outline.
  - Khong duoc truy cap cac route du lieu chi tiet (`/rooms`, `/tenants`, `/contracts`, `/electric`, `/bills`, `/invoice`).
  - Moi request ghi/sua/xoa qua API/POST se bi chan (HTTP 403).
- Dang nhap role `admin`: toan quyen thao tac.

Ngoai ra:
- CCCD va so dien thoai duoc ma hoa truoc khi luu.
- Co hash de tra cuu du lieu can thiet ma khong lo plaintext.

## 6) Trien khai nhanh (goi y)

- Push code len GitHub.
- Dung MongoDB Atlas cho database.
- Deploy web service tren Render/Railway/Fly (hoac Oracle VM neu can free on dinh 24/7).
- Cau hinh day du env vars nhu muc 4.2.

## 7) Ke hoach tiep theo

- Signup va quan ly nguoi dung nhieu vai tro (RBAC day du).
- JWT/session nang cao + refresh token.
- Audit log thao tac quan tri.
- Test tu dong (unit/integration) va CI/CD.
