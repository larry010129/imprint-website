/* 銘印鑽石｜註冊邀請碼驗證 — JS 版本，邏輯移植自 imprint-calculator 的 invites.py。
 * V3 沒有 Flask 版本的 role 欄位(admin/provider)，邀請碼「grants_admin」改成
 * 直接把新帳號寫進 staff_admins 表(跟 backend 既有的管理員判斷方式一致)。
 */
const crypto = require('crypto');

function inviteRequired() {
  if (['1', 'true', 'yes'].includes((process.env.REQUIRE_INVITE_CODE || '').trim().toLowerCase())) return true;
  return !!(process.env.REGISTRATION_INVITE_CODE || '').trim();
}

function timingSafeEqual(a, b) {
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

/** Returns an error message, or null if the code is acceptable (or not required). */
async function validateInviteCode(sql, code) {
  if (!inviteRequired()) return null;

  code = (code || '').trim();
  if (!code) return '請輸入邀請碼。 (Invite code is required.)';

  const envCode = (process.env.REGISTRATION_INVITE_CODE || '').trim();
  if (envCode && timingSafeEqual(code, envCode)) return null;

  const [invite] = await sql`select * from invite_codes where code = ${code}`;
  if (!invite) return '邀請碼無效或已過期。 (Invalid or expired invite code.)';
  if (!invite.is_active) return '邀請碼無效或已過期。 (Invalid or expired invite code.)';
  if (invite.expires_at && new Date(invite.expires_at) < new Date()) return '邀請碼無效或已過期。 (Invalid or expired invite code.)';
  if (invite.max_uses != null && invite.use_count >= invite.max_uses) return '邀請碼已達使用上限。 (Invite code has reached its use limit.)';
  return null;
}

/** Marks a DB-backed invite code as used (env codes aren't consumed). Returns whether it grants admin. */
async function consumeInviteCode(sql, code, userId) {
  code = (code || '').trim();
  const envCode = (process.env.REGISTRATION_INVITE_CODE || '').trim();
  if (envCode && timingSafeEqual(code, envCode)) return false;
  if (!code) return false;

  const [invite] = await sql`select * from invite_codes where code = ${code}`;
  if (!invite) return false;

  const newUseCount = (invite.use_count || 0) + 1;
  const stillActive = invite.max_uses != null ? newUseCount < invite.max_uses : invite.is_active;
  await sql`
    update invite_codes set use_count = ${newUseCount}, used_by_id = ${userId}, used_at = now(), is_active = ${stillActive}
    where id = ${invite.id}
  `;
  return !!invite.grants_admin;
}

function generateInviteCode() {
  return crypto.randomBytes(9).toString('base64url').slice(0, 12).toUpperCase();
}

module.exports = { inviteRequired, validateInviteCode, consumeInviteCode, generateInviteCode };
