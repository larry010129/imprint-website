const { sql } = require('../../lib/db');
const { requireAdmin } = require('../../lib/auth');
const { applyCors } = require('../../lib/cors');

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });

  const userId = await requireAdmin(req, res, sql);
  if (!userId) return;

  try {
    const [[{ count: newMessages }], [{ count: pendingQuotes }], [{ count: activeOrders }], [{ count: completedOrders }], monthlyTrend] =
      await Promise.all([
        sql`select count(*) from contact_messages where status = 'new'`,
        sql`select count(*) from quote_requests where status = 'pending'`,
        sql`select count(*) from orders where status <> 'completed'`,
        sql`select count(*) from orders where status = 'completed'`,
        // 簡化版月趨勢(移植自 dashboard.py build_dashboard_data 的精神，
        // 省略原本完整的 day/week/month 多粒度切換與 CSV 匯出)。
        sql`
          select to_char(created_at, 'YYYY-MM') as month,
                 count(*) as order_count,
                 coalesce(sum(total_price), 0) as revenue
          from orders
          where created_at >= now() - interval '6 months'
          group by 1 order by 1
        `,
      ]);

    res.status(200).json({
      newMessages: Number(newMessages),
      pendingQuotes: Number(pendingQuotes),
      activeOrders: Number(activeOrders),
      completedOrders: Number(completedOrders),
      monthlyTrend: monthlyTrend.map((r) => ({ month: r.month, orderCount: Number(r.order_count), revenue: Number(r.revenue) })),
    });
  } catch (err) {
    console.error('[admin/dashboard]', err);
    res.status(500).json({ error: '載入失敗' });
  }
};
