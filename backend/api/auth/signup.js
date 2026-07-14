const { sql } = require('../../lib/db');
const { hashPassword, signSession, setSessionCookie } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { checkRegisterLockout, recordFailure, recordSuccess, REGISTER_MAX_ATTEMPTS, REGISTER_LOCKOUT_SECONDS } = require('../../lib/rateLimit');
const { validateInviteCode, consumeInviteCode } = require('../../lib/invites');
const { logAdminAction } = require('../../lib/audit');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { email, password, fullName, phone, storeName, inviteCode } = req.body || {};
  if (!email || !password || !fullName || !phone) {
    return res.status(400).json({ error: '請完整填寫所有欄位' });
  }
  if (String(password).length < 6) {
    return res.status(400).json({ error: '密碼至少需要 6 碼' });
  }

  const normalizedEmail = String(email).trim().toLowerCase();

  try {
    const { key: lockoutKey, locked } = await checkRegisterLockout(sql, req);
    if (locked) {
      return res.status(429).json({ error: `註冊失敗次數過多，請 ${Math.ceil(REGISTER_LOCKOUT_SECONDS / 60)} 分鐘後再試` });
    }

    const inviteError = await validateInviteCode(sql, inviteCode);
    if (inviteError) {
      await recordFailure(sql, lockoutKey, { maxAttempts: REGISTER_MAX_ATTEMPTS, lockoutSeconds: REGISTER_LOCKOUT_SECONDS });
      return res.status(400).json({ error: inviteError });
    }

    const existing = await sql`select id from users where email = ${normalizedEmail}`;
    if (existing.length) {
      await recordFailure(sql, lockoutKey, { maxAttempts: REGISTER_MAX_ATTEMPTS, lockoutSeconds: REGISTER_LOCKOUT_SECONDS });
      return res.status(409).json({ error: '此 Email 已被註冊' });
    }

    const passwordHash = await hashPassword(password);
    const [user] = await sql`
      insert into users (email, password_hash, email_verified)
      values (${normalizedEmail}, ${passwordHash}, true)
      returning id, email
    `;
    await sql`insert into profiles (id, full_name, phone, store_name) values (${user.id}, ${fullName}, ${phone}, ${storeName || null})`;

    const grantsAdmin = await consumeInviteCode(sql, inviteCode, user.id);
    if (grantsAdmin) {
      await sql`insert into staff_admins (user_id) values (${user.id}) on conflict do nothing`;
      await logAdminAction(sql, { actorEmail: user.email, action: 'invite_granted_admin', detail: { userId: user.id } });
    }

    await recordSuccess(sql, lockoutKey);

    const token = signSession(user.id);
    setSessionCookie(res, token);
    res.status(200).json({ ok: true, user: { id: user.id, email: user.email } });
  } catch (err) {
    console.error('[signup]', err);
    res.status(500).json({ error: '註冊失敗，請稍後再試' });
  }
};
