/* 銘印鑽石｜登入/註冊失敗鎖定 — JS 版本，邏輯移植自 imprint-calculator 的
 * auth.py。原本用 process 記憶體內的 dict 存失敗次數，在 serverless
 * function 上每次呼叫都是新的 process，記憶體不會保留，所以改存在
 * Neon 的 login_lockouts 表(見 schema.sql)。
 */

const LOGIN_MAX_ATTEMPTS = 5;
const LOGIN_LOCKOUT_SECONDS = 300;
const REGISTER_MAX_ATTEMPTS = 10;
const REGISTER_LOCKOUT_SECONDS = 600;

function clientIp(req) {
  // Vercel sets x-forwarded-for; the first entry is the original client.
  const fwd = req.headers['x-forwarded-for'];
  if (fwd) return String(fwd).split(',')[0].trim();
  return req.socket && req.socket.remoteAddress || 'unknown';
}

async function isLockedOut(sql, key) {
  const [row] = await sql`select fail_count, locked_until from login_lockouts where lockout_key = ${key}`;
  if (!row) return false;
  if (row.fail_count >= 1 && row.locked_until && new Date(row.locked_until) > new Date()) {
    return row.fail_count; // truthy — still locked
  }
  return false;
}

async function recordFailure(sql, key, { maxAttempts, lockoutSeconds }) {
  const [row] = await sql`select fail_count from login_lockouts where lockout_key = ${key}`;
  const failCount = (row ? row.fail_count : 0) + 1;
  const lockedUntil = failCount >= maxAttempts
    ? new Date(Date.now() + lockoutSeconds * 1000).toISOString()
    : null;
  await sql`
    insert into login_lockouts (lockout_key, fail_count, locked_until, updated_at)
    values (${key}, ${failCount}, ${lockedUntil}, now())
    on conflict (lockout_key) do update set
      fail_count = ${failCount}, locked_until = ${lockedUntil}, updated_at = now()
  `;
}

async function recordSuccess(sql, key) {
  await sql`delete from login_lockouts where lockout_key = ${key}`;
}

/** Admin helper — clear lockouts for a username across all IPs. */
async function clearLoginLockout(sql, username) {
  await sql`delete from login_lockouts where lockout_key like ${'login:' + username.toLowerCase() + ':%'}`;
}

async function checkLoginLockout(sql, req, email) {
  const key = `login:${email.toLowerCase()}:${clientIp(req)}`;
  return { key, locked: await isLockedOut(sql, key) };
}

async function checkRegisterLockout(sql, req) {
  const key = `register:${clientIp(req)}`;
  return { key, locked: await isLockedOut(sql, key) };
}

module.exports = {
  LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS,
  clientIp, isLockedOut, recordFailure, recordSuccess, clearLoginLockout,
  checkLoginLockout, checkRegisterLockout,
};
