# Rental Management Dashboard (FastAPI + MongoDB)

Minimal rental management dashboard for boarding houses (nhà trọ).

Quick start

1. Create a Python virtualenv and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and edit values.

3. Run the app:

```bash
uvicorn app.main:app --reload --port 8000
```

4. Visit `http://localhost:8000` and login at `/login` (default admin/password)

Import Excel

```bash
python scripts/import_excel.py data.xlsx
```
