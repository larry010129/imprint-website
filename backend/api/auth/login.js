const { sql } = require('../../lib/db');
const { verifyPassword, signSession, setSessionCookie } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { checkLoginLockout, recordFailure, recordSuccess, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS } = require('../../lib/rateLimit');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { email, password } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: '請輸入 Email 與密碼' });

  const normalizedEmail = String(email).trim().toLowerCase();

  try {
    const { key: lockoutKey, locked } = await checkLoginLockout(sql, req, normalizedEmail);
    if (locked) {
      return res.status(429).json({ error: `登入失敗次數過多，請 ${Math.ceil(LOGIN_LOCKOUT_SECONDS / 60)} 分鐘後再試` });
    }

    const [user] = await sql`select id, email, password_hash from users where email = ${normalizedEmail}`;
    if (!user || !(await verifyPassword(password, user.password_hash))) {
      await recordFailure(sql, lockoutKey, { maxAttempts: LOGIN_MAX_ATTEMPTS, lockoutSeconds: LOGIN_LOCKOUT_SECONDS });
      return res.status(401).json({ error: 'Email 或密碼不正確' });
    }

    await recordSuccess(sql, lockoutKey);
    await sql`update users set last_login_at = now() where id = ${user.id}`;

    const token = signSession(user.id);
    setSessionCookie(res, token);
    res.status(200).json({ ok: true, user: { id: user.id, email: user.email } });
  } catch (err) {
    console.error('[login]', err);
    res.status(500).json({ error: '登入失敗，請稍後再試' });
  }
};
