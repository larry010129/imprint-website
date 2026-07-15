/* Admin dashboard line chart — port of diamond-calculator admin-dashboard.js, colorDNA tokens */
(function (global) {
  'use strict';

  var MINT = '#5ECFCF';
  var INK = '#2B2320';
  var OK = '#4CAF7D';
  var MUTED = '#8A817B';
  var GRID = 'rgba(43,35,32,.08)';

  var chartInstance = null;
  var trendView = 'period';
  var trendMetric = 'amount';
  var bound = false;
  var lastTrends = [];

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

  function buildChart(canvas, trends) {
    if (!canvas || typeof Chart === 'undefined' || !trends || !trends.length) return;

    var labels = trends.map(function (item) { return item.label || item.month; });
    var orderTotals = trends.map(function (item) { return item.orderTotal != null ? item.orderTotal : 0; });
    var revenue = trends.map(function (item) { return item.revenue != null ? item.revenue : 0; });
    var orderCounts = trends.map(function (item) { return item.orderCount != null ? item.orderCount : 0; });
    var completedCounts = trends.map(function (item) { return item.completedOrders != null ? item.completedOrders : 0; });

    var isCount = trendMetric === 'count';
    var ordersLabel = isCount ? '訂單數量' : '訂單總額';
    var revenueLabel = isCount ? '完成訂單數' : '完成營收';
    var suffix = trendView === 'cumulative' ? '（累計）' : '';

    var orderSeries = isCount ? orderCounts : orderTotals;
    var revenueSeries = isCount ? completedCounts : revenue;
    var orderData = trendView === 'cumulative' ? cumulative(orderSeries) : orderSeries;
    var revenueData = trendView === 'cumulative' ? cumulative(revenueSeries) : revenueSeries;

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(canvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: ordersLabel + suffix,
            data: orderData,
            borderColor: MINT,
            backgroundColor: 'rgba(94,207,207,.12)',
            tension: 0.35,
            pointRadius: 2,
            fill: true,
          },
          {
            label: revenueLabel + suffix,
            data: revenueData,
            borderColor: OK,
            backgroundColor: 'rgba(76,175,125,.1)',
            tension: 0.35,
            pointRadius: 2,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: MUTED, usePointStyle: true, boxWidth: 8 } },
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
              callback: function (v) { return formatValue(v, isCount); },
            },
            grid: { color: GRID },
          },
        },
      },
    });
  }

  function init(trends) {
    var canvas = document.getElementById('dashTrendsChart');
    var viewToggle = document.getElementById('dashTrendViewToggle');
    var metricToggle = document.getElementById('dashTrendMetricToggle');
    if (!canvas) return;

    lastTrends = trends || [];
    buildChart(canvas, lastTrends);

    if (bound) return;
    bound = true;

    if (viewToggle) {
      viewToggle.querySelectorAll('[data-trend-view]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (btn.dataset.trendView === trendView) return;
          trendView = btn.dataset.trendView;
          setActiveButton(viewToggle, btn);
          buildChart(canvas, lastTrends);
        });
      });
    }

    if (metricToggle) {
      metricToggle.querySelectorAll('[data-trend-metric]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (btn.dataset.trendMetric === trendMetric) return;
          trendMetric = btn.dataset.trendMetric;
          setActiveButton(metricToggle, btn);
          buildChart(canvas, lastTrends);
        });
      });
    }
  }

  global.AdminDashboardChart = { init: init };
})(window);
