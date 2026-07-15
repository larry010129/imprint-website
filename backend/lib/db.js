/* Neon connection. Uses @neondatabase/serverless HTTP driver (short-lived
 * serverless invocations) instead of a long-lived TCP pool.
 */
const { neon } = require('@neondatabase/serverless');

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL is not set (Neon connection string)');
}

const sql = neon(process.env.DATABASE_URL);

module.exports = { sql };
