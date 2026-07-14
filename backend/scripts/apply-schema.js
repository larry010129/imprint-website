#!/usr/bin/env node
/* Apply backend/schema.sql to Neon (one statement at a time). */
const fs = require('fs');
const path = require('path');
const { neon } = require('@neondatabase/serverless');

if (!process.env.DATABASE_URL) {
  console.error('DATABASE_URL is not set');
  process.exit(1);
}

const sql = neon(process.env.DATABASE_URL);

function parseStatements(fileText) {
  const withoutComments = fileText
    .split('\n')
    .filter((line) => !line.trim().startsWith('--'))
    .join('\n');
  return withoutComments
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean);
}

async function main() {
  const schemaPath = path.join(__dirname, '..', 'schema.sql');
  const statements = parseStatements(fs.readFileSync(schemaPath, 'utf8'));
  console.log(`Applying ${statements.length} SQL statement(s)…`);
  for (let i = 0; i < statements.length; i++) {
    const stmt = statements[i];
    try {
      await sql(stmt);
    } catch (err) {
      console.error(`Failed on statement ${i + 1}:`, stmt.slice(0, 80) + '…');
      throw err;
    }
  }
  console.log('Schema applied.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
