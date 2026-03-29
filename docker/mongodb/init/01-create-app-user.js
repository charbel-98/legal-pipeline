const appDatabase = process.env.MONGO_APP_DATABASE;
const appUsername = process.env.MONGO_APP_USERNAME;
const appPassword = process.env.MONGO_APP_PASSWORD;

if (!appDatabase || !appUsername || !appPassword) {
  throw new Error("Mongo app user environment variables are required for initialization.");
}

db = db.getSiblingDB(appDatabase);

db.createUser({
  user: appUsername,
  pwd: appPassword,
  roles: [
    {
      role: "readWrite",
      db: appDatabase,
    },
  ],
});
