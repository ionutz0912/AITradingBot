/**
 * Notifications History JavaScript
 *
 * All user content is sanitized via textContent to prevent XSS.
 */

const API_BASE = '/api';
const PAGE_SIZE = 50;
let currentOffset = 0;
let totalCount = 0;

// Type icons
const TYPE_ICONS = {
    'signal': '\u{1F4CA}',        // Chart
    'trade_opened': '\u{1F7E2}',  // Green circle
    'trade_closed': '\u{1F534}',  // Red circle
    'error': '\u26A0\uFE0F',      // Warning
    'daily_summary': '\u{1F4C8}', // Chart up
    'simulation_status': '\u{1F3AE}', // Game controller
    'test': '\u2705'              // Check mark
};

// Status colors
const STATUS_CLASSES = {
    'sent': 'status-sent',
    'failed': 'status-failed',
    'pending': 'status-pending',
    'skipped': 'status-skipped'
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadNotifications();
    // Refresh every 30 seconds
    setInterval(() => {
        loadStats();
        loadNotifications();
    }, 30000);
});

// Load notification statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/notifications/stats`);
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('stat-total').textContent = stats.total || 0;
            document.getElementById('stat-sent').textContent = stats.by_status?.sent || 0;
            document.getElementById('stat-failed').textContent = stats.by_status?.failed || 0;
            document.getElementById('stat-pending').textContent = stats.by_status?.pending || 0;
            document.getElementById('stat-recent-failures').textContent = stats.recent_failures_24h || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load notifications list
async function loadNotifications() {
    const status = document.getElementById('filter-status').value;
    const type = document.getElementById('filter-type').value;

    try {
        let url = `${API_BASE}/notifications?limit=${PAGE_SIZE}&offset=${currentOffset}`;
        if (status) url += `&status=${status}`;
        if (type) url += `&type=${type}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            renderNotifications(data.notifications);
            totalCount = data.count;
            updatePagination();
        } else {
            showError('Failed to load notifications');
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        showError('Error loading notifications');
    }
}

// Render notifications table using DOM methods
function renderNotifications(notifications) {
    const tbody = document.getElementById('notifications-table');

    // Clear table
    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }

    if (notifications.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 5;
        cell.className = 'text-center py-8 text-gray-500';
        cell.textContent = 'No notifications found';
        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }

    notifications.forEach(notif => {
        tbody.appendChild(createNotificationRow(notif));
    });
}

// Create a notification row
function createNotificationRow(notif) {
    const row = document.createElement('tr');
    row.className = 'border-b border-gray-700/50 hover:bg-gray-700/30';

    // Time column
    const timeCell = document.createElement('td');
    timeCell.className = 'py-3 px-4 whitespace-nowrap';
    timeCell.textContent = formatTime(notif.created_at);
    row.appendChild(timeCell);

    // Type column
    const typeCell = document.createElement('td');
    typeCell.className = 'py-3 px-4 whitespace-nowrap';

    const typeSpan = document.createElement('span');
    typeSpan.className = 'flex items-center gap-2';

    const icon = document.createElement('span');
    icon.textContent = TYPE_ICONS[notif.type] || '\u2139\uFE0F';

    const typeName = document.createElement('span');
    typeName.textContent = formatType(notif.type);

    typeSpan.appendChild(icon);
    typeSpan.appendChild(typeName);
    typeCell.appendChild(typeSpan);
    row.appendChild(typeCell);

    // Content column
    const contentCell = document.createElement('td');
    contentCell.className = 'py-3 px-4 max-w-md truncate';
    contentCell.title = notif.content;
    contentCell.textContent = truncateContent(notif.content);
    row.appendChild(contentCell);

    // Status column
    const statusCell = document.createElement('td');
    statusCell.className = 'py-3 px-4 whitespace-nowrap';

    const statusSpan = document.createElement('span');
    statusSpan.className = `${STATUS_CLASSES[notif.delivery_status] || ''} flex items-center gap-1`;

    const statusDot = document.createElement('span');
    statusDot.className = `w-2 h-2 rounded-full ${getStatusBgClass(notif.delivery_status)}`;

    const statusText = document.createElement('span');
    statusText.textContent = notif.delivery_status;

    statusSpan.appendChild(statusDot);
    statusSpan.appendChild(statusText);
    statusCell.appendChild(statusSpan);
    row.appendChild(statusCell);

    // Actions column
    const actionsCell = document.createElement('td');
    actionsCell.className = 'py-3 px-4 text-right whitespace-nowrap';

    const viewBtn = document.createElement('button');
    viewBtn.className = 'text-blue-400 hover:text-blue-300 mr-3';
    viewBtn.textContent = 'View';
    viewBtn.onclick = () => showDetails(notif.id);
    actionsCell.appendChild(viewBtn);

    if (notif.delivery_status === 'failed' || notif.delivery_status === 'pending') {
        const retryBtn = document.createElement('button');
        retryBtn.className = 'text-green-400 hover:text-green-300';
        retryBtn.textContent = 'Retry';
        retryBtn.onclick = () => retryNotification(notif.id);
        actionsCell.appendChild(retryBtn);
    }

    row.appendChild(actionsCell);

    return row;
}

// Get status background class
function getStatusBgClass(status) {
    switch (status) {
        case 'sent': return 'bg-green-500';
        case 'failed': return 'bg-red-500';
        case 'pending': return 'bg-yellow-500';
        case 'skipped': return 'bg-gray-500';
        default: return 'bg-gray-500';
    }
}

// Update pagination controls
function updatePagination() {
    const showing = Math.min(currentOffset + PAGE_SIZE, currentOffset + totalCount);
    document.getElementById('showing-count').textContent = `${currentOffset + 1}-${showing}`;

    document.getElementById('btn-prev').disabled = currentOffset === 0;
    document.getElementById('btn-next').disabled = totalCount < PAGE_SIZE;
}

// Pagination
function prevPage() {
    if (currentOffset > 0) {
        currentOffset = Math.max(0, currentOffset - PAGE_SIZE);
        loadNotifications();
    }
}

function nextPage() {
    if (totalCount >= PAGE_SIZE) {
        currentOffset += PAGE_SIZE;
        loadNotifications();
    }
}

// Show notification details
async function showDetails(id) {
    document.getElementById('detail-modal').classList.remove('hidden');
    document.getElementById('detail-modal').classList.add('flex');

    const content = document.getElementById('detail-content');
    content.textContent = 'Loading...';

    try {
        const response = await fetch(`${API_BASE}/notifications/${id}`);
        const data = await response.json();

        if (data.success) {
            renderDetailContent(data.notification);
        } else {
            content.textContent = 'Failed to load details';
        }
    } catch (error) {
        console.error('Error loading details:', error);
        content.textContent = 'Error loading details';
    }
}

// Render detail content using DOM methods
function renderDetailContent(notif) {
    const content = document.getElementById('detail-content');
    while (content.firstChild) {
        content.removeChild(content.firstChild);
    }

    // Status section
    const statusSection = document.createElement('div');
    statusSection.className = 'bg-gray-700 rounded-lg p-4 mb-4';

    const statusGrid = document.createElement('div');
    statusGrid.className = 'grid grid-cols-2 gap-4 text-sm';

    const fields = [
        { label: 'Type', value: formatType(notif.type) },
        { label: 'Status', value: notif.delivery_status, className: STATUS_CLASSES[notif.delivery_status] },
        { label: 'Created', value: formatTimeFull(notif.created_at) },
        { label: 'Sent', value: notif.sent_at ? formatTimeFull(notif.sent_at) : '-' },
        { label: 'Telegram ID', value: notif.telegram_message_id || '-' },
        { label: 'Retry Count', value: String(notif.retry_count || 0) }
    ];

    fields.forEach(field => {
        const div = document.createElement('div');

        const label = document.createElement('span');
        label.className = 'text-gray-400';
        label.textContent = field.label + ': ';

        const value = document.createElement('span');
        if (field.className) {
            value.className = field.className;
        }
        value.textContent = field.value;

        div.appendChild(label);
        div.appendChild(value);
        statusGrid.appendChild(div);
    });

    statusSection.appendChild(statusGrid);
    content.appendChild(statusSection);

    // Content section
    const contentSection = document.createElement('div');
    contentSection.className = 'bg-gray-700 rounded-lg p-4 mb-4';

    const contentTitle = document.createElement('h4');
    contentTitle.className = 'text-sm text-gray-400 mb-2';
    contentTitle.textContent = 'Content';

    const contentPre = document.createElement('pre');
    contentPre.className = 'text-sm whitespace-pre-wrap bg-gray-800 p-3 rounded overflow-x-auto';
    contentPre.textContent = notif.content;

    contentSection.appendChild(contentTitle);
    contentSection.appendChild(contentPre);
    content.appendChild(contentSection);

    // Error section if present
    if (notif.error_message) {
        const errorSection = document.createElement('div');
        errorSection.className = 'bg-red-900/30 border border-red-700 rounded-lg p-4 mb-4';

        const errorTitle = document.createElement('h4');
        errorTitle.className = 'text-sm text-red-400 mb-2';
        errorTitle.textContent = 'Error';

        const errorText = document.createElement('p');
        errorText.className = 'text-sm';
        errorText.textContent = notif.error_message;

        errorSection.appendChild(errorTitle);
        errorSection.appendChild(errorText);
        content.appendChild(errorSection);
    }

    // Actions
    if (notif.delivery_status === 'failed' || notif.delivery_status === 'pending') {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'flex justify-end';

        const retryBtn = document.createElement('button');
        retryBtn.className = 'bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-medium transition-colors';
        retryBtn.textContent = 'Retry Send';
        retryBtn.onclick = () => {
            retryNotification(notif.id);
            closeDetailModal();
        };

        actionsDiv.appendChild(retryBtn);
        content.appendChild(actionsDiv);
    }
}

// Close detail modal
function closeDetailModal() {
    document.getElementById('detail-modal').classList.add('hidden');
    document.getElementById('detail-modal').classList.remove('flex');
}

// Retry notification
async function retryNotification(id) {
    try {
        const response = await fetch(`${API_BASE}/notifications/${id}/retry`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showSuccess('Notification retry initiated');
            loadNotifications();
            loadStats();
        } else {
            showError(data.error || 'Failed to retry notification');
        }
    } catch (error) {
        console.error('Error retrying notification:', error);
        showError('Error retrying notification');
    }
}

// Send test notification
async function sendTestNotification() {
    try {
        const response = await fetch(`${API_BASE}/notifications/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: 'Test notification from Dashboard at ' + new Date().toLocaleString()
            })
        });

        const data = await response.json();

        if (data.success) {
            if (data.notification.delivery_status === 'sent') {
                showSuccess('Test notification sent successfully');
            } else if (data.notification.delivery_status === 'skipped') {
                showWarning('Telegram not configured - notification skipped');
            } else {
                showError('Test notification failed: ' + (data.notification.error_message || 'Unknown error'));
            }
            loadNotifications();
            loadStats();
        } else {
            showError(data.error || 'Failed to send test notification');
        }
    } catch (error) {
        console.error('Error sending test notification:', error);
        showError('Error sending test notification');
    }
}

// Utility functions
function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatTimeFull(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatType(type) {
    if (!type) return '-';
    return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function truncateContent(content, maxLength = 100) {
    if (!content) return '-';
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showError(message) {
    showToast(message, 'error');
}

function showWarning(message) {
    showToast(message, 'warning');
}

function showToast(message, type) {
    // Remove existing toasts
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const bgClass = {
        'success': 'bg-green-600',
        'error': 'bg-red-600',
        'warning': 'bg-yellow-600'
    }[type] || 'bg-gray-600';

    const toast = document.createElement('div');
    toast.className = `toast fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 ${bgClass}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}
