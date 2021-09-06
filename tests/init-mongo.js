db.auth(_getEnv("MONGO_INITDB_ROOT_USERNAME"), _getEnv("MONGO_INITDB_ROOT_PASSWORD"));

db = db.getSiblingDB(_getEnv("MONGO_DB"));

db.createUser({
  user: _getEnv("MONGO_INITDB_ROOT_USERNAME"),
  pwd: _getEnv("MONGO_INITDB_ROOT_PASSWORD"),
  roles: [
    {
      role: 'root',
      db: 'admin',
    },
  ],
});
