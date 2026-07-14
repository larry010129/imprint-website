/* POST {id, reason?}: admin deletes an order. If it belonged to a logged-in
 * customer, leaves them a notification (order_search.py / models.py's
 * UserNotification kind='order_removed' pattern) since the order itself is
 * gone and they'd otherwise never know why it disappeared from their account.
 */
const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');
const { logAdminAction } = require('../../lib/audit');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  const { id, reason } = req.body || {};
  if (!id) return res.status(400).json({ error: 'missing id' });

  try {
    const [order] = await sql`select * from orders where id = ${id}`;
    if (!order) return res.status(404).json({ error: 'order not found' });

    if (order.user_id) {
      const summary = [order.series, order.product_type].filter(Boolean).join(' ・ ') || order.order_number;
      const message = reason
        ? `您的訂單 ${order.order_number} 已被移除：${reason}`
        : `您的訂單 ${order.order_number} 已被移除。`;
      await sql`
        insert into user_notifications (user_id, kind, message, order_summary)
        values (${order.user_id}, 'order_removed', ${message}, ${summary})
      `;
    }

    await sql`delete from orders where id = ${id}`;
    await logAdminAction(sql, { action: 'order_deleted', detail: { orderId: id, orderNumber: order.order_number, reason: reason || null } });
    res.status(200).json({ ok: true });
  } catch (err) {
    console.error('[admin/order-delete]', err);
    res.status(500).json({ error: '刪除失敗' });
  }
};
