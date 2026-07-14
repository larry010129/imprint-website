/* Neon connection. Uses @neondatabase/serverless's HTTP-based driver instead
 * of a pooled TCP connection (pg) — the recommended approach for Neon in
 * serverless functions, since each Vercel invocation is short-lived and a
 * TCP pool would exhaust Neon's connection limit under concurrent requests.
 */
const { neon } = require('@neondatabase/serverless');

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is not set (Neon connection string)');
}

const sql = neon(process.env.DATABASE_URL);

module.exports = { sql };
