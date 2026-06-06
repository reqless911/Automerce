/**
 * charts.js — Automerce
 * Chart.js initialisation functions for the analytics dashboard.
 * Called from analytics.html after the page-level data variables are set.
 */

/**
 * Initialise the horizontal bar chart showing top products by view count.
 *
 * @param {string} canvasId  - ID of the <canvas> element
 * @param {Array}  labels    - Product name labels
 * @param {Array}  data      - View count values
 */
function initViewsChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Views',
                data: data,
                backgroundColor: 'rgba(46, 125, 159, 0.75)',
                borderColor: 'rgba(46, 125, 159, 1)',
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',   // horizontal bars
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ' ' + context.parsed.x + ' views';
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { precision: 0 }
                },
                y: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 12 },
                        callback: function(value, index) {
                            // Truncate long product names
                            const label = this.getLabelForValue(index);
                            return label.length > 20 ? label.substring(0, 18) + '…' : label;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialise the donut chart showing product count per category.
 *
 * @param {string} canvasId  - ID of the <canvas> element
 * @param {Array}  labels    - Category name labels
 * @param {Array}  data      - Product count values
 */
function initDonutChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const palette = [
        '#4e79a7', '#59a14f', '#f28e2b',
        '#e15759', '#76b7b2', '#edc948',
        '#b07aa1', '#ff9da7', '#9c755f'
    ];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: palette.slice(0, labels.length),
                borderColor: '#ffffff',
                borderWidth: 2,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 16,
                        font: { size: 12 },
                        usePointStyle: true,
                        pointStyleWidth: 10,
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0
                                ? Math.round((context.parsed / total) * 100)
                                : 0;
                            return ' ' + context.label + ': ' + context.parsed + ' (' + pct + '%)';
                        }
                    }
                }
            }
        }
    });
}