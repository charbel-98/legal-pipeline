// Create the application database and user from environment variables injected by Docker
// MONGO_APP_DATABASE, MONGO_APP_USERNAME, MONGO_APP_PASSWORD are set via docker-compose environment

const dbName = process.env.MONGO_APP_DATABASE;
const username = process.env.MONGO_APP_USERNAME;
const password = process.env.MONGO_APP_PASSWORD;

db = db.getSiblingDB(dbName);

db.createUser({
    user: username,
    pwd: password,
    roles: [{ role: "readWrite", db: dbName }],
});

// Landing zone collection for raw scraped metadata
db.createCollection("cases_landing");
db.cases_landing.createIndex({ identifier: 1 }, { unique: true });
db.cases_landing.createIndex({ partition_date: 1 });
db.cases_landing.createIndex({ body: 1 });

// Processed zone collection for transformed metadata
db.createCollection("cases_processed");
db.cases_processed.createIndex({ identifier: 1 }, { unique: true });
db.cases_processed.createIndex({ partition_date: 1 });
