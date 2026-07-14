const { sql } = require('../../lib/db');
const { generateResetToken } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

const RESET_TOKEN_TTL_HOURS = 1;

async function sendResetEmail(toEmail, resetUrl) {
  if (!process.env.RESEND_API_KEY) {
    console.warn('[request-password-reset] RESEND_API_KEY not set — email not sent. Reset URL:', resetUrl);
    return;
  }
  await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: process.env.RESET_EMAIL_FROM || 'noreply@imprint-diamond.com',
      to: toEmail,
      subject: '銘印鑽石｜重設密碼',
      html: `<p>請點擊以下連結重設您的密碼（1 小時內有效）：</p><p><a href="${resetUrl}">${resetUrl}</a></p>`,
    }),
  });
}

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { email } = req.body || {};
  // Always respond ok regardless of whether the email exists — avoids
  // leaking which emails are registered (email enumeration).
  if (!email) return res.status(200).json({ ok: true });

  try {
    const normalizedEmail = String(email).trim().toLowerCase();
    const [user] = await sql`select id from users where email = ${normalizedEmail}`;

    if (user) {
      const token = generateResetToken();
      const expiresAt = new Date(Date.now() + RESET_TOKEN_TTL_HOURS * 60 * 60 * 1000).toISOString();
      await sql`insert into password_reset_tokens (token, user_id, expires_at) values (${token}, ${user.id}, ${expiresAt})`;

      const siteUrl = process.env.SITE_URL || 'https://www.imprint-diamond.com';
      const resetUrl = `${siteUrl}/reset-password.html?token=${token}`;
      await sendResetEmail(normalizedEmail, resetUrl);
    }

    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[request-password-reset]', err);
    res.status(200).json({ ok: true }); // still don't leak failure details
  }
};
