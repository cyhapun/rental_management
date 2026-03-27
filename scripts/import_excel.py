"""
Import Excel into MongoDB Atlas (Production Ready)
"""

import os
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

from app.security import encrypt_value, hash_value

# LOAD ENV
load_dotenv()


def get_db():
    uri = os.getenv("MONGO_URI")
    dbname = os.getenv("MONGO_DB", "rental_db")

    if not uri:
        raise Exception("Missing MONGO_URI in .env")

    client = MongoClient(uri)
    return client[dbname]


def parse_date(d):
    try:
        if pd.isna(d):
            return None
        return pd.to_datetime(d)
    except:
        return None


def import_file(path):
    db = get_db()

    df = pd.read_excel(path)
    payments_cols = [c for c in df.columns if str(c).strip().startswith("Lần")]

    price_per_kwh = int(os.getenv("PRICE_PER_KWH", 3000))

    for idx, row in df.iterrows():
        print(f"Processing row {idx}")

        # ===== READ DATA =====
        room_number = row.get("Số phòng")
        cccd = row.get("CCCD")
        full_name = row.get("Họ và Tên")
        gender = row.get("Giới tính")
        birth_year = row.get("Năm sinh")
        phone = row.get("SDT")
        start_date = parse_date(row.get("Ngày Thuê"))
        end_date = parse_date(row.get("Ngày Kết Thúc"))
        contract_type = row.get("Loại Hợp Đồng")
        usage = row.get("Số kWh điện")

        if pd.isna(cccd):
            print(f"Skip row {idx}: missing CCCD")
            continue

        cccd_norm = str(cccd).strip()
        cccd_h = hash_value(cccd_norm)
        phone_norm = None if pd.isna(phone) else str(phone).strip()

        # ===== TENANT =====
        tenant = db.tenants.find_one({"cccd_hash": cccd_h}) if cccd_h else None
        if not tenant:
            # legacy plaintext fallback
            tenant = db.tenants.find_one({"cccd": cccd_norm})

        if not tenant:
            tenant_data = {
                "full_name": str(full_name) if not pd.isna(full_name) else "",
                "cccd": encrypt_value(cccd_norm, require_key=True),
                "cccd_hash": cccd_h,
                "gender": str(gender) if not pd.isna(gender) else None,
                "birth_year": int(birth_year) if not pd.isna(birth_year) else None,
                "phone": encrypt_value(phone_norm, require_key=True) if phone_norm else None,
                "phone_hash": hash_value(phone_norm) if phone_norm else None,
                "created_at": datetime.utcnow(),
            }
            tenant_id = db.tenants.insert_one(tenant_data).inserted_id
        else:
            # If the tenant exists but doesn't have hash fields (legacy plaintext), migrate to encrypted.
            if cccd_h and tenant.get("cccd_hash") != cccd_h:
                db.tenants.update_one(
                    {"_id": tenant["_id"]},
                    {
                        "$set": {
                            "cccd": encrypt_value(cccd_norm, require_key=True),
                            "cccd_hash": cccd_h,
                            "phone": encrypt_value(phone_norm, require_key=True) if phone_norm else None,
                            "phone_hash": hash_value(phone_norm) if phone_norm else None,
                        }
                    },
                )
            tenant_id = tenant["_id"]

        # ===== ROOM =====
        room = db.rooms.find_one({"room_number": str(room_number)})

        if not room:
            room_data = {
                "room_number": str(room_number),
                "price": 0,
                "status": "occupied",
                "created_at": datetime.utcnow(),
            }
            room_id = db.rooms.insert_one(room_data).inserted_id
        else:
            room_id = room["_id"]
            db.rooms.update_one(
                {"_id": room_id},
                {"$set": {"status": "occupied"}}
            )

        # ===== CONTRACT =====
        contract_data = {
            "tenant_id": tenant_id,
            "room_id": room_id,
            "start_date": start_date,
            "end_date": end_date,
            "contract_type": contract_type if not pd.isna(contract_type) else None,
            "deposit": 0,
            "created_at": datetime.utcnow(),
        }
        contract_id = db.contracts.insert_one(contract_data).inserted_id

        # ===== ELECTRIC =====
        month = start_date.strftime("%Y-%m") if start_date else ""

        electric_cost = 0
        if not pd.isna(usage):
            usage = int(usage)
            electric_cost = usage * price_per_kwh

            db.electric_readings.insert_one({
                "room_id": room_id,
                "month": month,
                "old_index": 0,
                "new_index": usage,
                "usage": usage,
                "price_per_kwh": price_per_kwh,
                "created_at": datetime.utcnow(),
            })

        # ===== BILL =====
        bill_data = {
            "contract_id": contract_id,
            "month": month,
            "room_price": 0,
            "electric_cost": electric_cost,
            "water_cost": 0,
            "other_cost": 0,
            "total": electric_cost,
            "status": "unpaid",
            "created_at": datetime.utcnow(),
        }
        bill_id = db.bills.insert_one(bill_data).inserted_id

        # ===== PAYMENTS =====
        for pc in payments_cols:
            val = row.get(pc)
            if not pd.isna(val) and float(val) > 0:
                db.payments.insert_one({
                    "bill_id": bill_id,
                    "amount": float(val),
                    "payment_date": datetime.utcnow(),
                    "method": "import",
                })

    print("Import completed successfully!")

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("file", help="Excel file path")

args = parser.parse_args()
import_file(args.file)