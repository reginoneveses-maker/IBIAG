// Only a new, isolated candidate volume. Never import or modify an existing IBIAG database.
const password=process.env.IBIAG_DB_PASSWORD;
if(!password||!/^([a-f0-9]{64})$/.test(password))throw new Error('Candidate database credentials missing or invalid');
db.getSiblingDB('ibiag_candidate').createUser({user:'ibiag_app',pwd:password,roles:[{role:'readWrite',db:'ibiag_candidate'}]});
