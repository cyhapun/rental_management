# MongoDB Indexing for Nha_tro Web

This file provides recommended index commands and verification steps.

Run the script in `scripts/create_indexes.js` with `mongosh` or run the commands below in Mongo shell/Compass.

Recommended index commands:

```js
db.bills.createIndex({ "month": -1, "status": 1 });
db.electric_readings.createIndex({ "room_id": 1, "month": -1 });
db.contracts.createIndex({ "room_id": 1, "tenant_id": 1 });
```

How to run (examples):

- Using mongosh and a connection string that includes the database:

```
mongosh "mongodb+srv://<user>:<pass>@cluster0/mydatabase" --file scripts/create_indexes.js
```

- Or open MongoDB Compass, connect to the cluster, open the database and run the commands in the "Playground" or "Shell".

Verification:

- Check created indexes:

```js
db.bills.getIndexes();
db.electric_readings.getIndexes();
db.contracts.getIndexes();
```

- Use `explain()` to verify queries use the index. Example:

```js
db.bills.find({ month: "2026-03" }).explain("executionStats")
```

Notes & cautions:
- Indexes speed up reads but increase write cost and disk usage. Add only indexes you need.
- After creating indexes, run `explain()` on slow queries to confirm the index is used.
- Consider TTL or partial indexes for time-based data to reduce index size.
