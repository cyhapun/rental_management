import os
import sys
import json
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, '..', '.env'))

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')

if not MONGO_URI or not MONGO_DB:
    print('MONGO_URI or MONGO_DB not set in .env')
    sys.exit(1)

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

if len(sys.argv) < 2:
    print('Usage: python scripts/normalize_bills.py <contract_id_or_bill_id_orroom>')
    sys.exit(1)

ident = sys.argv[1]

# collect bills to update
bills = []
# Try find by bill _id
try:
    b = db.bills.find_one({'_id': ObjectId(ident)})
    if b:
        bills.append(b)
except Exception:
    pass

# try by contract_id
cursor = db.bills.find({'$or': [{'contract_id': ident}, {'contract_id': str(ident)}]})
for b in cursor:
    bills.append(b)

# try by room_id
cursor = db.bills.find({'$or': [{'room_id': ident}, {'room_id': str(ident)}]})
for b in cursor:
    bills.append(b)

if not bills:
    print('No bills found for identifier', ident)
    sys.exit(0)

print(f'Found {len(bills)} bills. Processing...')

for b in bills:
    bid = b.get('_id')
    updates = {}
    if 'electric_cost' not in b and 'electric_amount' in b:
        try:
            updates['electric_cost'] = int(b.get('electric_amount') or 0)
        except Exception:
            updates['electric_cost'] = 0
    if 'room_price' not in b and 'rent_amount' in b:
        try:
            updates['room_price'] = int(b.get('rent_amount') or 0)
        except Exception:
            updates['room_price'] = 0
    if 'water_cost' not in b and 'water_amount' in b:
        try:
            updates['water_cost'] = int(b.get('water_amount') or 0)
        except Exception:
            updates['water_cost'] = 0
    if 'total' not in b and 'total_amount' in b:
        try:
            updates['total'] = int(b.get('total_amount') or 0)
        except Exception:
            updates['total'] = 0

    # infer total if still missing
    if 'total' not in updates:
        rp = int(b.get('room_price') or b.get('rent_amount') or 0)
        ec = int(b.get('electric_cost') or b.get('electric_amount') or 0)
        wc = int(b.get('water_cost') or b.get('water_amount') or 0)
        oc = int(b.get('other_cost') or 0)
        if rp or ec or wc or oc:
            updates['total'] = rp + ec + wc + oc

    if updates:
        print(f'Updating bill {bid}:', updates)
        try:
            db.bills.update_one({'_id': bid}, {'$set': updates})
        except Exception as e:
            print('Failed update', bid, e)

print('Done')
