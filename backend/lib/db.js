/* Supabase Postgres via postgres.js (tagged-template SQL, neon-compatible). */
const postgres = require('postgres');

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is not set (Supabase Postgres connection string)');
}

const dsn = process.env.DATABASE_URL;
const isPooler = /pooler\.supabase\.com|:6543/.test(dsn);

const sql = postgres(dsn, {
  ssl: 'require',
  max: Number(process.env.PG_POOL_MAX || 1),
  idle_timeout: 20,
  connect_timeout: 10,
  prepare: isPooler ? false : true,
});

module.exports = { sql };
