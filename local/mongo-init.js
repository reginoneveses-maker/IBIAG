// Runs only for a new, empty local Docker volume.
const password = process.env.IBIAG_DB_PASSWORD;
if (!password || !/^[a-f0-9]{64}$/.test(password)) {
  throw new Error("Local database configuration is missing or invalid");
}
db.getSiblingDB("ibiag_local").createUser({
  user: "ibiag_app",
  pwd: password,
  roles: [{role: "readWrite", db: "ibiag_local"}]
});
