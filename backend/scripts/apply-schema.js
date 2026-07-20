#!/usr/bin/env node
/* Apply backend/schema.sql to Supabase Postgres (one statement at a time). */
const fs = require('fs');
const path = require('path');
const { sql } = require('../lib/db');

function parseStatements(fileText) {
  // Strip `--` comments (including trailing inline ones) before splitting on
  // `;` — a `;` inside a comment must not be treated as a statement terminator.
  const withoutComments = fileText
    .split('\n')
    .map((line) => line.replace(/--.*$/, ''))
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
      await sql.unsafe(stmt);
    } catch (err) {
      console.error(`Failed on statement ${i + 1}:`, stmt.slice(0, 80) + '…');
      throw err;
    }
  }
  console.log('Schema applied.');
  await sql.end({ timeout: 5 });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
