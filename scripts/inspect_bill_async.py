import os
import sys
import json
import asyncio
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, '..', '.env'))

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')

if not MONGO_URI or not MONGO_DB:
    print('MONGO_URI or MONGO_DB not set in .env')
    sys.exit(1)


def _make_printable(doc: dict) -> dict:
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        else:
            out[k] = v
    return out


async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]

    if len(sys.argv) < 2:
        print('Usage: python scripts/inspect_bill_async.py <contract_id_or_room_id>')
        return

    ident = sys.argv[1]

    try:
        oid = ObjectId(ident)
    except Exception:
        oid = None

    print('Searching contract(s) for:', ident)
    contracts = []
    if oid:
        c = await db.contracts.find_one({'_id': oid})
        if c:
            contracts.append(c)

    cursor = db.contracts.find({'$or': [{'_id': ident}, {'room_id': ident}, {'tenant_id': ident}]})
    async for c in cursor:
        contracts.append(c)

    if not contracts:
        print('No contracts found with that identifier')
        return

    for c in contracts:
        print('\n--- Contract ---')
        print(json.dumps(_make_printable(c), default=str, indent=2))
        cid = str(c.get('_id'))
        print('\nBills for contract', cid)

        b_cursor = db.bills.find({'$or': [{'contract_id': cid}, {'contract_id': c.get('_id')}]})
        b_cursor = b_cursor.sort([('month', -1), ('created_at', -1)]).limit(10)
        async for b in b_cursor:
            print(json.dumps(b, default=str, indent=2))

        # show latest electric readings for the room
        room_id = c.get('room_id')
        print('\nLatest electric readings for room', room_id)
        or_clauses = []
        if room_id is not None:
            or_clauses.append({'room_id': room_id})
            or_clauses.append({'room_id': str(room_id)})
        try:
            room = await db.rooms.find_one({'_id': ObjectId(room_id)})
            if room:
                rn = room.get('room_number')
                or_clauses.append({'room_id': rn})
                or_clauses.append({'room_id': str(rn)})
        except Exception:
            pass

        if or_clauses:
            er_cursor = db.electric_readings.find({'$or': or_clauses}).sort([('month', -1), ('_id', -1)]).limit(10)
            async for er in er_cursor:
                print(json.dumps(er, default=str, indent=2))

    print('\nDone')


if __name__ == '__main__':
    asyncio.run(main())
