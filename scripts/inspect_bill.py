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
    print('Usage: python scripts/inspect_bill.py <contract_id_or_room_id>')
    sys.exit(1)

ident = sys.argv[1]

# Try to resolve as ObjectId, otherwise treat as string
try:
    oid = ObjectId(ident)
except Exception:
    oid = None

print('Searching contract(s) for:', ident)
contracts = []
if oid:
    c = db.contracts.find_one({'_id': oid})
    if c:
        contracts.append(c)
# Also try string match
cursor = db.contracts.find({'$or':[{'_id': ident}, {'room_id': ident}, {'tenant_id': ident}]})
for c in cursor:
    contracts.append(c)

if not contracts:
    print('No contracts found with that identifier')
    sys.exit(0)

for c in contracts:
    print('\n--- Contract ---')
    print(json.dumps({k: (str(v) if k=='_id' or isinstance(v, ObjectId) else v) for k,v in c.items()}, default=str, indent=2))
    cid = str(c.get('_id'))
    print('\nBills for contract', cid)
    for b in db.bills.find({'$or':[{'contract_id': cid},{'contract_id': c.get('_id')}] }).sort([('month', -1), ('created_at', -1)])[:10]:
        print(json.dumps(b, default=str, indent=2))
    # show latest electric readings for the room
    room_id = c.get('room_id')
    print('\nLatest electric readings for room', room_id)
    or_clauses = []
    if room_id is not None:
        or_clauses.append({'room_id': room_id})
        or_clauses.append({'room_id': str(room_id)})
    try:
        room = db.rooms.find_one({'_id': ObjectId(room_id)})
        if room:
            rn = room.get('room_number')
            or_clauses.append({'room_id': rn})
            or_clauses.append({'room_id': str(rn)})
    except Exception:
        pass
    if or_clauses:
        for er in db.electric_readings.find({'$or': or_clauses}).sort([('month', -1), ('_id', -1)])[:10]:
            print(json.dumps(er, default=str, indent=2))

print('\nDone')
