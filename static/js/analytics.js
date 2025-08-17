// Mock data for dashboard (replace with API calls when backend is ready)
const mockDashboardData = {
    learninglocker_data: {
        sync_status: {
            learninglocker_sync: {
                total_synced: 12345,
                last_sync_time: '2024-08-04 15:30',
            }
        },
        statement_stats: {
            total_statements: 54321,
            statements_today: 123,
            unique_actors: 42,
            completion_rate: 87.2
        }
    },
    performance_metrics: {
        system_performance: {
            cpu_usage: 23,
            memory_usage: 68,
            response_time_ms: 120
        },
        user_activity: {
            total_sessions: 17
        },
        sync_performance: {
            sync_success_rate: 97.5,
            statements_per_minute: 56
        },
        data_quality: {
            valid_statements: 99.1,
            average_score: 85.7
        }
    }
};

const mockActivityData = {
    activity_data: Array.from({length: 30}, (_, i) => ({
        date: `2024-07-${(i+1).toString().padStart(2, '0')}`,
        statements: Math.floor(Math.random()*100+50),
        completions: Math.floor(Math.random()*50+20),
        attempts: Math.floor(Math.random()*80+30)
    }))
};

const mockSyncTimeline = {
    timeline: [
        {timestamp: Date.now()-3600000*3, status: 'success', message: 'Sync completed', statements_processed: 1200, duration_ms: 800, failed_count: 0},
        {timestamp: Date.now()-3600000*2, status: 'warning', message: 'Sync completed with warnings', statements_processed: 1100, duration_ms: 950, failed_count: 2},
        {timestamp: Date.now()-3600000, status: 'error', message: 'Sync failed', statements_processed: 0, duration_ms: 0, failed_count: 0},
    ]
};

let activityChart;

document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    loadActivityChart();
    loadSyncTimeline();
});

// Replace mock data with real API calls
async function loadDashboardData() {
    try {
        const response = await fetch('/metrics');
        const data = await response.json();
        updateDashboard({
            learninglocker_data: {
                sync_status: {
                    learninglocker_sync: {
                        total_synced: data.data_metrics.statements_flat_count,
                        last_sync_time: data.timestamp,
                    }
                },
                statement_stats: {
                    total_statements: data.data_metrics.statements_flat_count,
                    statements_today: 0, // Add if available
                    unique_actors: data.data_metrics.actors_count,
                    completion_rate: 0 // Add if available
                }
            },
            performance_metrics: {
                system_performance: {
                    cpu_usage: data.system_health.cpu_percent,
                    memory_usage: data.system_health.memory_percent,
                    response_time_ms: 0 // Add if available
                },
                user_activity: {
                    total_sessions: 0 // Add if available
                },
                sync_performance: {
                    sync_success_rate: 0, // Add if available
                    statements_per_minute: data.data_metrics.processing_rate
                },
                data_quality: {
                    valid_statements: 0, // Add if available
                    average_score: 0 // Add if available
                }
            }
        });
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        updateDashboard(mockDashboardData);
    }
}

function updateDashboard(data) {
    // Update Learning Locker sync data
    const syncStatus = data.learninglocker_data?.sync_status?.learninglocker_sync || {};
    document.getElementById('total-synced').textContent = syncStatus.total_synced || 0;
    document.getElementById('last-sync').textContent = syncStatus.last_sync_time || 'Never';

    // Update statement stats
    const statementStats = data.learninglocker_data?.statement_stats || {};
    document.getElementById('total-statements').textContent = statementStats.total_statements || 0;
    document.getElementById('today-statements').textContent = statementStats.statements_today || 0;
    document.getElementById('unique-users').textContent = statementStats.unique_actors || 0;
    document.getElementById('completion-rate').textContent = (statementStats.completion_rate || 0) + '%';

    // Update performance metrics
    const performance = data.performance_metrics || {};
    document.getElementById('cpu-usage').textContent = (performance.system_performance?.cpu_usage || 0) + '%';
    document.getElementById('memory-usage').textContent = (performance.system_performance?.memory_usage || 0) + '%';
    document.getElementById('response-time').textContent = (performance.system_performance?.response_time_ms || 0) + 'ms';
    document.getElementById('active-sessions').textContent = performance.user_activity?.total_sessions || 0;

    // Update performance cards
    document.getElementById('sync-performance').textContent = (performance.sync_performance?.sync_success_rate || 0) + '%';
    document.getElementById('statements-per-minute').textContent = performance.sync_performance?.statements_per_minute || 0;
    document.getElementById('data-quality').textContent = (performance.data_quality?.valid_statements || 0) + '%';
    document.getElementById('avg-score').textContent = performance.data_quality?.average_score || 0;
}

async function loadActivityChart() {
    try {
        const response = await fetch('/analytics');
        const data = await response.json();
        // Example: Use top_activities for chart
        const labels = data.insights.top_activities.map(a => a.activity);
        const counts = data.insights.top_activities.map(a => a.count);
        const ctx = document.getElementById('activityChart').getContext('2d');
        if (activityChart) activityChart.destroy();
        activityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Engagement Count',
                        data: counts,
                        backgroundColor: 'rgba(52, 152, 219, 0.5)',
                        borderColor: '#3498db',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: { display: true, text: 'Top Activities (24h)' }
                },
                scales: { y: { beginAtZero: true } }
            }
        });
    } catch (error) {
        console.error('Failed to load activity chart:', error);
        setTimeout(() => {
            const data = mockActivityData;
            const ctx = document.getElementById('activityChart').getContext('2d');
            if (activityChart) activityChart.destroy();
            activityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.activity_data.map(d => d.date),
                    datasets: [
                        {
                            label: 'Total Statements',
                            data: data.activity_data.map(d => d.statements),
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: 'Completions',
                            data: data.activity_data.map(d => d.completions),
                            borderColor: '#27ae60',
                            backgroundColor: 'rgba(39, 174, 96, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: 'Attempts',
                            data: data.activity_data.map(d => d.attempts),
                            borderColor: '#f39c12',
                            backgroundColor: 'rgba(243, 156, 18, 0.1)',
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                        title: { display: true, text: 'Statement Activity Over Time' }
                    },
                    scales: { y: { beginAtZero: true } }
                }
            });
        }, 300);
    }
}

function loadSyncTimeline() {
    // Simulate async fetch
    setTimeout(() => {
        const data = mockSyncTimeline;
        const timelineContainer = document.getElementById('sync-timeline');
        timelineContainer.innerHTML = '';
        data.timeline.forEach(item => {
            const timelineItem = document.createElement('div');
            timelineItem.className = `timeline-item ${item.status}`;
            const icon = item.status === 'success' ? '✅' : item.status === 'warning' ? '⚠️' : '❌';
            timelineItem.innerHTML = `
                <div class="timeline-icon">${icon}</div>
                <div class="timeline-content">
                    <div class="timeline-time">${new Date(item.timestamp).toLocaleString()}</div>
                    <div class="timeline-message">${item.message}</div>
                    <div class="timeline-stats">
                        ${item.statements_processed} statements processed in ${item.duration_ms}ms
                        ${item.failed_count ? `(${item.failed_count} failed)` : ''}
                    </div>
                </div>
            `;
            timelineContainer.appendChild(timelineItem);
        });
    }, 300);
}

function refreshDashboard() {
    loadDashboardData();
    loadActivityChart();
    loadSyncTimeline();
}

// Auto-refresh every 30 seconds
setInterval(refreshDashboard, 30000);