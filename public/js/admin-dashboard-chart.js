/* Admin dashboard chart. One chart area shows the series for whichever stat card is selected
   (營收 / 訂單 / 平均完成訂單 / 待處理 / 網站瀏覽量 / 不重複訪客). */
(function (global) {
  'use strict';

  var MINT = '#5ECFCF';
  var OK = '#4CAF7D';
  var BLUE = '#4A7FB5';
  var AMBER = '#D9A441';
  var MUTED = '#8A817B';
  var GRID = 'rgba(43,35,32,.08)';

  /* `toggles` = which of the chart's switches apply to this series. */
  var SERIES = {
    revenue:  { title: '營收趨勢', sub: '訂單與完成營收', toggles: { metric: true, view: true } },
    orders:   { title: '訂單趨勢', sub: '訂單數量與完成訂單數', toggles: { view: true } },
    average:  { title: '平均完成訂單趨勢', sub: '每期已完成訂單的平均金額', toggles: {} },
    pending:  { title: '待處理分布', sub: '目前待處理的留言、估價與進行中訂單（即時數字，不隨區間變動）', toggles: {}, noRange: true },
    views:    { title: '網站瀏覽量趨勢', sub: '每期頁面瀏覽次數', toggles: { view: true } },
    visitors: { title: '不重複訪客趨勢', sub: '每期每日不重複訪客加總', toggles: { view: true } },
  };

  var chartInstance = null;
  var selected = 'revenue';
  var trendView = 'period';
  var trendMetric = 'amount';
  var bound = false;
  var lastTrends = [];
  var lastContext = {};

  function cumulative(values) {
    var running = 0;
    return values.map(function (v) {
      running += v;
      return running;
    });
  }

  function setActiveButton(group, activeBtn) {
    if (!group) return;
    group.querySelectorAll('[data-trend-view],[data-trend-metric]').forEach(function (btn) {
      var active = btn === activeBtn;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  function formatValue(value, isCount) {
    if (isCount) return Number(value).toLocaleString('zh-TW');
    return 'NT$ ' + Number(value).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
  }

  function num(value) { return value != null ? Number(value) : 0; }

  function rangeText(trends, granularity) {
    var n = trends.length;
    if (granularity === 'day') return n + ' 天';
    if (granularity === 'week') return '近 ' + n + ' 週';
    return '近 ' + n + ' 個月';
  }

  /* visits.trend rows are keyed like the order buckets (same bucketKeys). */
  function visitSeries(trends, field) {
    var byKey = {};
    ((lastContext.visits && lastContext.visits.trend) || []).forEach(function (row) { byKey[row.key] = row; });
    return trends.map(function (item) {
      var row = byKey[item.month];
      return row ? num(row[field]) : 0;
    });
  }

  function lineDataset(label, data, color, fillColor) {
    return {
      label: label,
      data: data,
      borderColor: color,
      backgroundColor: fillColor,
      tension: 0.35,
      pointRadius: 2,
      fill: true,
    };
  }

  /* Everything the chart needs for one series: type, labels, datasets, number format. */
  function seriesConfig(key, trends) {
    var labels = trends.map(function (item) { return item.label || item.month; });
    var suffix = trendView === 'cumulative' ? '（累計）' : '';
    var apply = function (values) { return trendView === 'cumulative' ? cumulative(values) : values; };

    if (key === 'orders') {
      return {
        type: 'line', labels: labels, isCount: true,
        datasets: [
          lineDataset('訂單數量' + suffix, apply(trends.map(function (t) { return num(t.orderCount); })), MINT, 'rgba(94,207,207,.12)'),
          lineDataset('完成訂單數' + suffix, apply(trends.map(function (t) { return num(t.completedOrders); })), OK, 'rgba(76,175,125,.1)'),
        ],
      };
    }
    if (key === 'average') {
      var avg = trends.map(function (t) {
        var done = num(t.completedOrders);
        return done > 0 ? Math.round(num(t.revenue) / done) : 0;
      });
      return {
        type: 'line', labels: labels, isCount: false,
        datasets: [lineDataset('平均完成訂單', avg, BLUE, 'rgba(74,127,181,.12)')],
      };
    }
    if (key === 'views' || key === 'visitors') {
      var field = key === 'views' ? 'views' : 'uniques';
      return {
        type: 'line', labels: labels, isCount: true,
        datasets: [lineDataset((key === 'views' ? '網站瀏覽量' : '不重複訪客') + suffix,
          apply(visitSeries(trends, field)), MINT, 'rgba(94,207,207,.12)')],
      };
    }
    if (key === 'pending') {
      var p = lastContext.pending || {};
      return {
        type: 'bar', labels: ['新留言', '待處理估價', '進行中訂單'], isCount: true, hideLegend: true,
        datasets: [{
          label: '目前數量',
          data: [num(p.messages), num(p.quotes), num(p.active)],
          backgroundColor: [MINT, AMBER, BLUE],
          borderRadius: 6,
          maxBarThickness: 90,
        }],
      };
    }
    /* revenue: the original two-line chart */
    var isCount = trendMetric === 'count';
    var orderSeries = trends.map(function (t) { return isCount ? num(t.orderCount) : num(t.orderTotal); });
    var revenueSeries = trends.map(function (t) { return isCount ? num(t.completedOrders) : num(t.revenue); });
    return {
      type: 'line', labels: labels, isCount: isCount,
      datasets: [
        lineDataset((isCount ? '訂單數量' : '訂單總額') + suffix, apply(orderSeries), MINT, 'rgba(94,207,207,.12)'),
        lineDataset((isCount ? '完成訂單數' : '完成營收') + suffix, apply(revenueSeries), OK, 'rgba(76,175,125,.1)'),
      ],
    };
  }

  function buildChart(canvas, trends) {
    if (!canvas || typeof Chart === 'undefined') return;
    if (selected !== 'pending' && (!trends || !trends.length)) return;
    trends = trends || [];

    var cfg = seriesConfig(selected, trends);
    var isCount = cfg.isCount;
    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(canvas, {
      type: cfg.type,
      data: { labels: cfg.labels, datasets: cfg.datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: cfg.hideLegend ? { display: false } : { labels: { color: MUTED, usePointStyle: true, boxWidth: 8 } },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ': ' + formatValue(ctx.parsed.y, isCount);
              },
            },
          },
        },
        scales: {
          x: {
            ticks: { color: MUTED, maxRotation: 45, minRotation: 0, font: { size: 11 } },
            grid: { color: GRID },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: MUTED,
              font: { size: 11 },
              precision: 0,
              callback: function (v) { return formatValue(v, isCount); },
            },
            grid: { color: GRID },
          },
        },
      },
    });
  }

  /* Title, subtitle, which switches are visible, and which card is highlighted. */
  function updateChrome() {
    var def = SERIES[selected];
    var title = document.getElementById('dashChartTitle');
    var sub = document.getElementById('dashChartSub');
    if (title) title.textContent = def.title;
    if (sub) {
      sub.textContent = def.noRange
        ? def.sub
        : def.sub + '（' + rangeText(lastTrends, lastContext.granularity) + '）';
    }
    var metricToggle = document.getElementById('dashTrendMetricToggle');
    var viewToggle = document.getElementById('dashTrendViewToggle');
    if (metricToggle) metricToggle.hidden = !def.toggles.metric;
    if (viewToggle) viewToggle.hidden = !def.toggles.view;
    document.querySelectorAll('.dash-metric[data-chart]').forEach(function (card) {
      var active = card.getAttribute('data-chart') === selected;
      card.classList.toggle('is-active', active);
      card.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  function redraw() {
    var canvas = document.getElementById('dashTrendsChart');
    updateChrome();
    buildChart(canvas, lastTrends);
  }

  function select(key, opts) {
    if (!SERIES[key]) return;
    selected = key;
    redraw();
    var card = document.querySelector('.dash-chart-card');
    if (opts && opts.reveal && card && card.scrollIntoView) {
      card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  /* trends: stats.monthlyTrend. context: { granularity, visits, pending: {messages, quotes, active} }. */
  function init(trends, context) {
    var canvas = document.getElementById('dashTrendsChart');
    var viewToggle = document.getElementById('dashTrendViewToggle');
    var metricToggle = document.getElementById('dashTrendMetricToggle');
    if (!canvas) return;

    lastTrends = trends || [];
    lastContext = context || {};
    redraw();

    if (bound) return;
    bound = true;

    if (viewToggle) {
      viewToggle.querySelectorAll('[data-trend-view]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (btn.dataset.trendView === trendView) return;
          trendView = btn.dataset.trendView;
          setActiveButton(viewToggle, btn);
          redraw();
        });
      });
    }

    if (metricToggle) {
      metricToggle.querySelectorAll('[data-trend-metric]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (btn.dataset.trendMetric === trendMetric) return;
          trendMetric = btn.dataset.trendMetric;
          setActiveButton(metricToggle, btn);
          redraw();
        });
      });
    }
  }

  /* Cards are static HTML, so one document-level handler covers click, Enter and Space. */
  document.addEventListener('click', function (e) {
    var card = e.target.closest && e.target.closest('.dash-metric[data-chart]');
    if (card) select(card.getAttribute('data-chart'), { reveal: true });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var card = e.target.classList && e.target.classList.contains('dash-metric') && e.target.hasAttribute('data-chart')
      ? e.target : null;
    if (!card) return;
    e.preventDefault();
    select(card.getAttribute('data-chart'), { reveal: true });
  });

  global.AdminDashboardChart = { init: init, select: select };
})(window);
