// MongoDB index creation script
// Run with: mongosh "<connection-string>" < scripts/create_indexes.js

// NOTE: replace `your_database` with your database name if not using a connection URI
try {
  // If running with a connection string that includes db, you may skip `use`
  // e.g. mongosh "mongodb+srv://user:pass@cluster/dbname" --file scripts/create_indexes.js
  print('Creating indexes...');

  db.bills.createIndex({ "month": -1, "status": 1 });
  print('Created index on bills: { month: -1, status: 1 }');

  db.electric_readings.createIndex({ "room_id": 1, "month": -1 });
  print('Created index on electric_readings: { room_id: 1, month: -1 }');

  db.contracts.createIndex({ "room_id": 1, "tenant_id": 1 });
  print('Created index on contracts: { room_id: 1, tenant_id: 1 }');

  print('All indexes created. Run db.collection.getIndexes() to verify.');
} catch (err) {
  print('Error creating indexes: ' + err);
  throw err;
}
