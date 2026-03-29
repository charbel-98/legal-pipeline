# MongoDB Connections

This project now defines two MongoDB connection modes:

## 1. Application User

This is the user the scraper app should use.

Connection string:

```text
mongodb://<MONGO_APP_USERNAME>:<MONGO_APP_PASSWORD>@localhost:27018/legal_pipeline?authSource=legal_pipeline
```

Permissions:

- read/write on `legal_pipeline` only

Use this in:

- `.env`
- application runtime
- normal data inspection in Compass

## 2. Admin User

This is the root MongoDB user created by Docker initialization.

Connection string:

```text
mongodb://<MONGO_ROOT_USERNAME>:<MONGO_ROOT_PASSWORD>@localhost:27018/?authSource=admin
```

Permissions:

- full administrative access

Use this only when:

- you need DB admin access
- you want to inspect server-level state

## Important Note

If MongoDB data already exists in `mongo_data/`, the init script for the app user may not run automatically because Mongo only executes init scripts on first database initialization.

If that happens, recreate the Mongo container volume:

```bash
docker compose down -v
docker compose up -d
```

That will rebuild MongoDB from scratch and create the app user.
