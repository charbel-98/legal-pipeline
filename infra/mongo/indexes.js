// Index definitions for the legal_cases database.
// Applied automatically by init-mongo.js on first container start.

const dbName = process.env.MONGO_APP_DATABASE;
db = db.getSiblingDB(dbName);

// Landing zone indexes
db.cases_landing.createIndex({ identifier: 1 }, { unique: true });
db.cases_landing.createIndex({ partition_date: 1 });
db.cases_landing.createIndex({ body: 1 });
// Compound index for the transformation query: {partition_date: X, body: Y}
db.cases_landing.createIndex({ partition_date: 1, body: 1 });

// Processed zone indexes
db.cases_processed.createIndex({ identifier: 1 }, { unique: true });
db.cases_processed.createIndex({ partition_date: 1 });
db.cases_processed.createIndex({ body: 1 });
// Compound index for queries filtering by both partition and body
db.cases_processed.createIndex({ partition_date: 1, body: 1 });
