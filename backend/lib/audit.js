/* 銘印鑽石｜管理員操作稽核紀錄 — 邏輯移植自 imprint-calculator 的 audit.py。
 * 原本寫進 process log；這裡寫進 audit_log 資料表，讓後台可以直接查詢
 * (Flask 版本只能查伺服器 log 檔，這裡改進為可查詢的資料表)。
 */
async function logAdminAction(sql, { actorEmail, action, detail = {}, ip }) {
  try {
    await sql`
      insert into audit_log (actor_email, action, detail, ip)
      values (${actorEmail || 'unknown'}, ${action}, ${JSON.stringify(detail)}::jsonb, ${ip || null})
    `;
  } catch (err) {
    // Never let audit logging break the actual request.
    console.error('[audit] failed to write:', err);
  }
}

module.exports = { logAdminAction };
