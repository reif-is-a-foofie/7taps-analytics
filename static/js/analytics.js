/**
 * Enhanced Analytics Dashboard JavaScript
 * Provides interactive functionality for charts, data loading, and real-time updates
 */

class EnhancedAnalytics {
    constructor() {
        this.charts = {};
        this.autoRefreshInterval = null;
        this.baseUrl = window.location.origin;
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.setupAutoRefresh();
    }
    
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.querySelector('.refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshDashboard());
        }
        
        // Tab navigation
        const navLinks = document.querySelectorAll('[data-bs-toggle="pill"]');
        navLinks.forEach(link => {
            link.addEventListener('shown.bs.tab', (e) => {
                this.onTabChange(e.target.getAttribute('href'));
            });
        });
        
        // Export functionality
        const exportButtons = document.querySelectorAll('[data-export]');
        exportButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const format = e.target.getAttribute('data-export');
                this.exportData(format);
            });
        });
    }
    
    async loadInitialData() {
        try {
            this.showLoading(true);
            const data = await this.fetchDashboardData();
            this.updateDashboard(data);
        } catch (error) {
            this.showError('Failed to load dashboard data: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async fetchDashboardData() {
        const response = await fetch(`${this.baseUrl}/api/enhanced-dashboard/data`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const result = await response.json();
        
        if (result.status !== 'success') {
            throw new Error(result.message || 'Failed to fetch data');
        }
        
        return result.data;
    }
    
    updateDashboard(data) {
        this.updateMetrics(data);
        this.updateCharts(data);
        this.updateActivityFeed(data);
        this.updateLastUpdated();
        this.updateHealthIndicators(data);
    }
    
    updateMetrics(data) {
        const metrics = data.metrics?.metrics || {};
        
        // Update key metrics
        this.updateMetric('total-statements', metrics.total_statements || metrics.statements || '-');
        this.updateMetric('active-users', metrics.active_users_7d || metrics.active_users || '-');
        this.updateMetric('completion-rate', (metrics.completion_rate || 0) + '%');
        
        // System status
        const systemStatus = data.system_health?.status || 'unknown';
        this.updateSystemStatus(systemStatus);
    }
    
    updateMetric(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
            element.classList.add('fade-in');
            setTimeout(() => element.classList.remove('fade-in'), 300);
        }
    }
    
    updateSystemStatus(status) {
        const statusElement = document.getElementById('system-status');
        if (statusElement) {
            statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            statusElement.className = 'metric-value status-' + status;
        }
    }
    
    updateCharts(data) {
        this.updateActivityChart(data);
        this.updateActivitiesChart(data);
        this.updateCohortChart(data);
        this.updateEngagementChart(data);
        this.updateLearnerChart(data);
        this.updatePerformanceChart(data);
    }
    
    updateActivityChart(data) {
        const ctx = document.getElementById('activityChart');
        if (!ctx) return;
        
        const dailyActivity = data.metrics?.metrics?.daily_activity || [];
        const labels = dailyActivity.map(item => item.date || item.day);
        const values = dailyActivity.map(item => item.count || item.value);
        
        this.createOrUpdateChart('activityChart', {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Activity',
                    data: values,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    
    updateActivitiesChart(data) {
        const ctx = document.getElementById('activitiesChart');
        if (!ctx) return;
        
        const topVerbs = data.metrics?.metrics?.top_verbs || [];
        const labels = topVerbs.map(item => item.verb || item.name);
        const values = topVerbs.map(item => item.count || item.value);
        
        this.createOrUpdateChart('activitiesChart', {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
                        '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    updateCohortChart(data) {
        const ctx = document.getElementById('cohortChart');
        if (!ctx) return;
        
        const cohorts = data.metrics?.metrics?.cohort_completion || [];
        const labels = cohorts.map(item => item.cohort_name || item.name);
        const values = cohorts.map(item => item.completion_rate || item.value);
        
        this.createOrUpdateChart('cohortChart', {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Completion Rate (%)',
                    data: values,
                    backgroundColor: '#2563eb',
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    
    updateEngagementChart(data) {
        const ctx = document.getElementById('engagementChart');
        if (!ctx) return;
        
        // Sample engagement data - replace with real data when available
        const engagementData = {
            labels: ['Very Low', 'Low', 'Medium', 'High', 'Very High'],
            datasets: [{
                label: 'Learner Engagement',
                data: [5, 15, 30, 35, 15],
                backgroundColor: [
                    '#ef4444', '#f59e0b', '#eab308', '#10b981', '#2563eb'
                ],
                borderRadius: 6
            }]
        };
        
        this.createOrUpdateChart('engagementChart', {
            type: 'bar',
            data: engagementData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    
    updateLearnerChart(data) {
        const ctx = document.getElementById('learnerChart');
        if (!ctx) return;
        
        // Sample learner progress data - replace with real data when available
        const progressData = {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            datasets: [{
                label: 'Average Progress',
                data: [25, 45, 70, 85],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };
        
        this.createOrUpdateChart('learnerChart', {
            type: 'line',
            data: progressData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    
    updatePerformanceChart(data) {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;
        
        const performance = data.performance || {};
        const labels = ['CPU', 'Memory', 'Disk', 'Network'];
        const values = [
            performance.cpu_percent || 0,
            performance.memory_percent || 0,
            performance.disk_percent || 0,
            performance.network_usage || 0
        ];
        
        this.createOrUpdateChart('performanceChart', {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'System Performance',
                    data: values,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.2)',
                    pointBackgroundColor: '#2563eb',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        pointLabels: {
                            font: {
                                size: 12
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    createOrUpdateChart(chartId, config) {
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
        }
        
        const ctx = document.getElementById(chartId);
        if (ctx) {
            this.charts[chartId] = new Chart(ctx, config);
        }
    }
    
    updateActivityFeed(data) {
        const feedElement = document.getElementById('activity-feed');
        if (!feedElement) return;
        
        const realTime = data.real_time || {};
        const activities = realTime.recent_activities || [];
        
        if (activities.length === 0) {
            feedElement.innerHTML = '<div class="text-center text-muted">No recent activity</div>';
            return;
        }
        
        const feedHTML = activities.map(activity => `
            <div class="activity-item d-flex align-items-center py-2 border-bottom slide-in">
                <div class="status-indicator status-healthy"></div>
                <div class="flex-grow-1">
                    <div class="fw-medium">${activity.action || 'Activity'}</div>
                    <small class="text-muted">${activity.timestamp || 'Just now'}</small>
                </div>
            </div>
        `).join('');
        
        feedElement.innerHTML = feedHTML;
    }
    
    updateHealthIndicators(data) {
        const healthElement = document.getElementById('db-health');
        if (!healthElement) return;
        
        const systemHealth = data.system_health || {};
        const healthData = [
            { label: 'Database', value: systemHealth.database_connected ? 'Connected' : 'Disconnected', status: systemHealth.database_connected ? 'healthy' : 'error' },
            { label: 'Redis', value: systemHealth.redis_connected ? 'Connected' : 'Disconnected', status: systemHealth.redis_connected ? 'healthy' : 'error' },
            { label: 'API', value: systemHealth.api_status || 'Unknown', status: systemHealth.api_status === 'healthy' ? 'healthy' : 'warning' },
            { label: 'Uptime', value: systemHealth.uptime || '0s', status: 'healthy' }
        ];
        
        const healthHTML = healthData.map(item => `
            <div class="health-item">
                <div class="health-label">
                    <span class="status-indicator status-${item.status}"></span>
                    ${item.label}
                </div>
                <div class="health-value">${item.value}</div>
            </div>
        `).join('');
        
        healthElement.innerHTML = healthHTML;
    }
    
    updateLastUpdated() {
        const now = new Date().toLocaleString();
        const element = document.getElementById('last-updated');
        if (element) {
            element.textContent = now;
        }
    }
    
    onTabChange(tabId) {
        // Trigger chart resize when tab becomes visible
        setTimeout(() => {
            Object.values(this.charts).forEach(chart => {
                if (chart) {
                    chart.resize();
                }
            });
        }, 100);
    }
    
    async refreshDashboard() {
        if (this.isLoading) return;
        
        try {
            this.isLoading = true;
            const data = await this.fetchDashboardData();
            this.updateDashboard(data);
        } catch (error) {
            this.showError('Failed to refresh dashboard: ' + error.message);
        } finally {
            this.isLoading = false;
        }
    }
    
    setupAutoRefresh() {
        // Clear existing interval
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        // Set new interval (30 seconds)
        this.autoRefreshInterval = setInterval(() => {
            this.refreshDashboard();
        }, 30000);
    }
    
    async exportData(format = 'json') {
        try {
            const response = await fetch(`${this.baseUrl}/api/enhanced-dashboard/export?format=${format}`);
            const result = await response.json();
            
            if (result.status === 'success') {
                this.downloadFile(result.data, `analytics-export-${new Date().toISOString().split('T')[0]}.${format}`);
            } else {
                this.showError('Failed to export data');
            }
        } catch (error) {
            this.showError('Export failed: ' + error.message);
        }
    }
    
    downloadFile(content, filename) {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
    
    showLoading(show) {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) {
            spinner.style.display = show ? 'block' : 'none';
        }
    }
    
    showError(message) {
        const errorElement = document.getElementById('error-message');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                this.hideError();
            }, 5000);
        }
    }
    
    hideError() {
        const errorElement = document.getElementById('error-message');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }
}

// Initialize enhanced analytics when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.enhancedAnalytics = new EnhancedAnalytics();
});

// Global refresh function for button onclick
function refreshDashboard() {
    if (window.enhancedAnalytics) {
        window.enhancedAnalytics.refreshDashboard();
    }
}
