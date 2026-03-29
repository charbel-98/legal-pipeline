const appDatabase = process.env.MONGO_APP_DATABASE || "legal_pipeline";
const appUsername = process.env.MONGO_APP_USERNAME || "legal_pipeline_user";
const appPassword = process.env.MONGO_APP_PASSWORD || "legal_pipeline_pass";

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
