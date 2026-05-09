import os
import sys
import json
import asyncio
import datetime
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


async def main():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]

    if len(sys.argv) < 2:
        print('Usage: python scripts/create_bill_from_reading_async.py <contract_id> [month]')
        return

    contract_ident = sys.argv[1]
    month = sys.argv[2] if len(sys.argv) >= 3 else datetime.datetime.now().strftime('%Y-%m')

    contract = None
    try:
        contract = await db.contracts.find_one({'_id': ObjectId(contract_ident)})
    except Exception:
        pass
    if not contract:
        contract = await db.contracts.find_one({'_id': contract_ident})
    if not contract:
        print('Contract not found')
        return

    room_id = contract.get('room_id')
    room = None
    try:
        room = await db.rooms.find_one({'_id': ObjectId(room_id)})
    except Exception:
        room = await db.rooms.find_one({'_id': room_id})

    room_number = room.get('room_number') if room else None

    or_clauses = []
    if room_id is not None:
        or_clauses.append({'room_id': room_id})
        or_clauses.append({'room_id': str(room_id)})
    if room_number is not None:
        or_clauses.append({'room_id': room_number})
        or_clauses.append({'room_id': str(room_number)})

    reading = None
    if or_clauses:
        reading = await db.electric_readings.find_one({'$and': [{'month': month}, {'$or': or_clauses}]})
    if not reading and or_clauses:
        reading = await db.electric_readings.find_one({'$or': or_clauses}, sort=[('month', -1), ('_id', -1)])

    if not reading:
        print('No electric reading found for contract room. Cannot create bill automatically.')
        return

    prev_index = int(reading.get('old_index', 0) or 0)
    curr_index = int(reading.get('new_index', prev_index) or prev_index)
    usage = int(reading.get('usage', max(0, curr_index - prev_index)))
    kwh_price = int(reading.get('price_per_kwh', os.getenv('PRICE_PER_KWH') or 3000))
    electric_cost = int(reading.get('total', usage * kwh_price))

    water_fee = int(os.getenv('WATER_FEE') or 50000)
    room_price = 0
    if room:
        try:
            room_price = int(room.get('price', 0) or 0)
        except Exception:
            room_price = 0

    total = room_price + electric_cost + water_fee

    bill_doc = {
        'contract_id': str(contract.get('_id')),
        'room_id': str(room.get('_id')) if room else room_id,
        'tenant_id': contract.get('tenant_id'),
        'month': month,
        'room_price': room_price,
        'electric_cost': electric_cost,
        'water_cost': water_fee,
        'other_cost': 0,
        'total': total,
        'status': 'unpaid',
        'type': 'liquidation',
        'created_at': datetime.datetime.utcnow(),
        'prev_index': prev_index,
        'curr_index': curr_index,
        'usage': usage,
        'kwh_price': kwh_price
    }

    res = await db.bills.insert_one(bill_doc)
    print('Inserted bill id:', str(res.inserted_id))
    print(json.dumps(bill_doc, default=str, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
