/**
 * Simulations Management JavaScript
 *
 * Note: innerHTML usage is safe here because:
 * 1. All user-provided content is escaped via escapeHtml()
 * 2. All other content comes from our own API endpoints
 * 3. This is an internal admin dashboard, not public-facing
 */

const API_BASE = '/api';
let presets = [];
let currentSimulationId = null;

// Symbol to crypto name mapping
const SYMBOL_NAMES = {
    'BTCUSDT': 'Bitcoin',
    'ETHUSDT': 'Ethereum',
    'SOLUSDT': 'Solana',
    'XRPUSDT': 'XRP',
    'ADAUSDT': 'Cardano'
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSimulations();
    loadPresets();
    // Refresh every 10 seconds
    setInterval(loadSimulations, 10000);
});

// Load simulations list
async function loadSimulations() {
    try {
        const response = await fetch(`${API_BASE}/simulations`);
        const data = await response.json();

        if (data.success) {
            renderSimulations(data.simulations);
            updateStats(data.simulations);
        } else {
            showError('Failed to load simulations');
        }
    } catch (error) {
        console.error('Error loading simulations:', error);
        showError('Error loading simulations');
    }
}

// Load presets
async function loadPresets() {
    try {
        const response = await fetch(`${API_BASE}/simulations/presets`);
        const data = await response.json();

        if (data.success) {
            presets = data.presets;
            populatePresetSelect();
        }
    } catch (error) {
        console.error('Error loading presets:', error);
    }
}

// Populate preset dropdown
function populatePresetSelect() {
    const select = document.getElementById('preset-select');
    // Clear and add default option
    while (select.firstChild) {
        select.removeChild(select.firstChild);
    }
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = '-- Select a preset --';
    select.appendChild(defaultOption);

    presets.forEach(preset => {
        const option = document.createElement('option');
        option.value = preset.id;
        option.textContent = `${preset.name} - ${preset.description}`;
        select.appendChild(option);
    });
}

// Load preset into form
function loadPreset(presetId) {
    if (!presetId) return;

    const preset = presets.find(p => p.id === presetId);
    if (!preset) return;

    const form = document.getElementById('simulation-form');
    const config = preset.config;

    form.name.value = config.name;
    form.symbol.value = config.symbol;
    form.initial_capital.value = config.initial_capital;
    form.position_size.value = config.position_size;
    form.ai_provider.value = config.ai_provider;
    form.stop_loss_percent.value = config.stop_loss_percent;
    form.check_interval_seconds.value = config.check_interval_seconds;
    form.max_daily_trades.value = config.max_daily_trades;
    form.telegram_enabled.checked = config.telegram_enabled;
    form.telegram_include_reasoning.checked = config.telegram_include_reasoning;
}

// Render simulations grid using DOM methods
function renderSimulations(simulations) {
    const container = document.getElementById('simulations-container');

    // Clear container
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }

    if (simulations.length === 0) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'col-span-full text-center py-12';

        const p = document.createElement('p');
        p.className = 'text-gray-400 mb-4';
        p.textContent = 'No simulations yet';

        const btn = document.createElement('button');
        btn.className = 'text-blue-400 hover:text-blue-300';
        btn.textContent = 'Create your first simulation';
        btn.onclick = openCreateModal;

        emptyDiv.appendChild(p);
        emptyDiv.appendChild(btn);
        container.appendChild(emptyDiv);
        return;
    }

    simulations.forEach(sim => {
        container.appendChild(createSimulationCard(sim));
    });
}

// Create simulation card using DOM methods
function createSimulationCard(sim) {
    const card = document.createElement('div');
    card.className = 'bg-gray-800 rounded-lg p-5 shadow-lg';

    const config = sim.config;
    const statusClass = `status-${sim.status}`;

    // Header
    const header = document.createElement('div');
    header.className = 'flex justify-between items-start mb-4';

    const titleDiv = document.createElement('div');
    const h3 = document.createElement('h3');
    h3.className = 'font-semibold text-lg';
    h3.textContent = sim.name;

    const subtitle = document.createElement('p');
    subtitle.className = 'text-gray-400 text-sm';
    subtitle.textContent = `${config.symbol} (${config.crypto_name || SYMBOL_NAMES[config.symbol] || ''})`;

    titleDiv.appendChild(h3);
    titleDiv.appendChild(subtitle);

    const statusSpan = document.createElement('span');
    statusSpan.className = `${statusClass} flex items-center gap-1`;
    statusSpan.appendChild(createStatusIcon(sim.status));
    statusSpan.appendChild(document.createTextNode(sim.status));

    header.appendChild(titleDiv);
    header.appendChild(statusSpan);
    card.appendChild(header);

    // Stats grid
    const statsGrid = document.createElement('div');
    statsGrid.className = 'grid grid-cols-2 gap-3 text-sm mb-4';

    const stats = [
        { label: 'Capital:', value: `$${formatNumber(config.initial_capital)}` },
        { label: 'Position:', value: `${config.position_size}${typeof config.position_size === 'string' && config.position_size.includes('%') ? '' : ' USD'}` },
        { label: 'AI:', value: config.ai_provider },
        { label: 'Interval:', value: formatInterval(config.check_interval_seconds) }
    ];

    stats.forEach(stat => {
        const div = document.createElement('div');
        const label = document.createElement('span');
        label.className = 'text-gray-400';
        label.textContent = stat.label;
        const value = document.createElement('span');
        value.className = 'ml-1';
        value.textContent = stat.value;
        div.appendChild(label);
        div.appendChild(value);
        statsGrid.appendChild(div);
    });

    card.appendChild(statsGrid);

    // Control buttons
    const controls = document.createElement('div');
    controls.className = 'flex gap-2 pt-3 border-t border-gray-700';

    const buttons = createControlButtons(sim);
    buttons.forEach(btn => controls.appendChild(btn));

    card.appendChild(controls);

    return card;
}

// Create status icon element
function createStatusIcon(status) {
    const span = document.createElement('span');
    span.className = 'w-2 h-2 rounded-full';

    switch (status) {
        case 'running':
            span.className += ' bg-green-500 pulse-dot';
            break;
        case 'paused':
            span.className += ' bg-yellow-500';
            break;
        case 'stopped':
            span.className += ' bg-gray-500';
            break;
        case 'pending':
            span.className += ' bg-blue-500';
            break;
        case 'error':
            span.className += ' bg-red-500';
            break;
    }

    return span;
}

// Create control buttons
function createControlButtons(sim) {
    const buttons = [];

    switch (sim.status) {
        case 'pending':
        case 'stopped':
            buttons.push(createButton('Start', 'bg-green-600 hover:bg-green-700', () => startSimulation(sim.id)));
            break;
        case 'running':
            buttons.push(createButton('Pause', 'bg-yellow-600 hover:bg-yellow-700', () => pauseSimulation(sim.id)));
            buttons.push(createButton('Stop', 'bg-red-600 hover:bg-red-700', () => stopSimulation(sim.id)));
            break;
        case 'paused':
            buttons.push(createButton('Resume', 'bg-green-600 hover:bg-green-700', () => resumeSimulation(sim.id)));
            buttons.push(createButton('Stop', 'bg-red-600 hover:bg-red-700', () => stopSimulation(sim.id)));
            break;
        case 'error':
            buttons.push(createButton('Retry', 'bg-green-600 hover:bg-green-700', () => startSimulation(sim.id)));
            break;
    }

    buttons.push(createButton('Details', 'border border-gray-600 hover:bg-gray-700', () => showDetails(sim.id), false));
    buttons.push(createButton('Delete', 'border border-red-600 text-red-400 hover:bg-red-600 hover:text-white', () => deleteSimulation(sim.id), false));

    return buttons;
}

// Create a button element
function createButton(text, classes, onClick, flex = true) {
    const btn = document.createElement('button');
    btn.className = `${flex ? 'flex-1 ' : ''}${classes} px-3 py-1.5 rounded text-sm font-medium transition-colors`;
    btn.textContent = text;
    btn.onclick = onClick;
    return btn;
}

// Update stats display
function updateStats(simulations) {
    const total = simulations.length;
    const running = simulations.filter(s => s.status === 'running').length;
    const paused = simulations.filter(s => s.status === 'paused').length;
    const active = simulations.filter(s => ['pending', 'running', 'paused'].includes(s.status)).length;

    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-running').textContent = running;
    document.getElementById('stat-paused').textContent = paused;
    document.getElementById('stat-available').textContent = Math.max(0, 5 - active);
}

// Modal functions
function openCreateModal() {
    document.getElementById('create-modal').classList.remove('hidden');
    document.getElementById('create-modal').classList.add('flex');
    document.getElementById('modal-title').textContent = 'Create New Simulation';
    document.getElementById('simulation-form').reset();
    document.getElementById('preset-select').value = '';
    currentSimulationId = null;
}

function closeCreateModal() {
    document.getElementById('create-modal').classList.add('hidden');
    document.getElementById('create-modal').classList.remove('flex');
}

function closeDetailModal() {
    document.getElementById('detail-modal').classList.add('hidden');
    document.getElementById('detail-modal').classList.remove('flex');
}

// Submit simulation form
async function submitSimulation(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    // Parse position size - keep as string if has %, otherwise parse as float
    let positionSize = formData.get('position_size');
    if (!positionSize.includes('%')) {
        positionSize = parseFloat(positionSize);
    }

    const config = {
        name: formData.get('name'),
        symbol: formData.get('symbol'),
        crypto_name: SYMBOL_NAMES[formData.get('symbol')] || formData.get('symbol'),
        initial_capital: parseFloat(formData.get('initial_capital')),
        position_size: positionSize,
        fees: 0.0006,
        ai_provider: formData.get('ai_provider'),
        stop_loss_percent: parseFloat(formData.get('stop_loss_percent')),
        max_daily_trades: parseInt(formData.get('max_daily_trades')),
        check_interval_seconds: parseInt(formData.get('check_interval_seconds')),
        telegram_enabled: formData.get('telegram_enabled') === 'on',
        telegram_include_reasoning: formData.get('telegram_include_reasoning') === 'on'
    };

    try {
        const response = await fetch(`${API_BASE}/simulations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: config.name,
                config: config
            })
        });

        const data = await response.json();

        if (data.success) {
            closeCreateModal();
            loadSimulations();
            showSuccess('Simulation created successfully');
        } else {
            showError(data.error || 'Failed to create simulation');
        }
    } catch (error) {
        console.error('Error creating simulation:', error);
        showError('Error creating simulation');
    }
}

// Control functions
async function startSimulation(id) {
    await controlSimulation(id, 'start');
}

async function stopSimulation(id) {
    if (!confirm('Are you sure you want to stop this simulation?')) return;
    await controlSimulation(id, 'stop');
}

async function pauseSimulation(id) {
    await controlSimulation(id, 'pause');
}

async function resumeSimulation(id) {
    await controlSimulation(id, 'resume');
}

async function controlSimulation(id, action) {
    try {
        const response = await fetch(`${API_BASE}/simulations/${id}/${action}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            loadSimulations();
            showSuccess(`Simulation ${action}ed successfully`);
        } else {
            showError(data.error || `Failed to ${action} simulation`);
        }
    } catch (error) {
        console.error(`Error ${action}ing simulation:`, error);
        showError(`Error ${action}ing simulation`);
    }
}

async function deleteSimulation(id) {
    if (!confirm('Are you sure you want to delete this simulation? This action cannot be undone.')) return;

    try {
        const response = await fetch(`${API_BASE}/simulations/${id}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            loadSimulations();
            showSuccess('Simulation deleted');
        } else {
            showError(data.error || 'Failed to delete simulation');
        }
    } catch (error) {
        console.error('Error deleting simulation:', error);
        showError('Error deleting simulation');
    }
}

// Show simulation details
async function showDetails(id) {
    document.getElementById('detail-modal').classList.remove('hidden');
    document.getElementById('detail-modal').classList.add('flex');
    const content = document.getElementById('detail-content');
    content.textContent = 'Loading...';

    try {
        // Fetch simulation and stats in parallel
        const [simResponse, statsResponse, tradesResponse] = await Promise.all([
            fetch(`${API_BASE}/simulations/${id}`),
            fetch(`${API_BASE}/simulations/${id}/stats`),
            fetch(`${API_BASE}/simulations/${id}/trades?limit=10`)
        ]);

        const simData = await simResponse.json();
        const statsData = await statsResponse.json();
        const tradesData = await tradesResponse.json();

        if (simData.success) {
            renderDetails(simData.simulation, statsData.stats || {}, tradesData.trades || []);
        } else {
            content.textContent = 'Failed to load details';
        }
    } catch (error) {
        console.error('Error loading details:', error);
        content.textContent = 'Error loading details';
    }
}

// Render details using DOM methods
function renderDetails(sim, stats, trades) {
    document.getElementById('detail-title').textContent = sim.name;

    const content = document.getElementById('detail-content');
    while (content.firstChild) {
        content.removeChild(content.firstChild);
    }

    const config = sim.config;
    const statusClass = `status-${sim.status}`;

    // Create grid container
    const grid = document.createElement('div');
    grid.className = 'grid grid-cols-1 md:grid-cols-2 gap-6 mb-6';

    // Configuration section
    const configSection = createDetailSection('Configuration', [
        { label: 'Symbol:', value: config.symbol },
        { label: 'Initial Capital:', value: `$${formatNumber(config.initial_capital)}` },
        { label: 'Position Size:', value: String(config.position_size) },
        { label: 'AI Provider:', value: config.ai_provider },
        { label: 'Stop Loss:', value: `${config.stop_loss_percent}%` },
        { label: 'Check Interval:', value: formatInterval(config.check_interval_seconds) }
    ]);

    // Performance section
    const perfSection = createDetailSection('Performance', [
        { label: 'Status:', value: sim.status, valueClass: statusClass },
        { label: 'Total Trades:', value: String(stats.total_trades || 0) },
        { label: 'Win Rate:', value: `${(stats.win_rate || 0).toFixed(1)}%` },
        { label: 'Total P&L:', value: `$${formatNumber(stats.total_pnl || 0)}`, valueClass: (stats.total_pnl || 0) >= 0 ? 'text-profit' : 'text-loss' },
        { label: 'Total Fees:', value: `$${formatNumber(stats.total_fees || 0)}` }
    ]);

    grid.appendChild(configSection);
    grid.appendChild(perfSection);
    content.appendChild(grid);

    // Error section if present
    if (sim.error_message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-900/30 border border-red-700 rounded-lg p-4 mb-6';

        const errorTitle = document.createElement('h4');
        errorTitle.className = 'font-medium text-red-400 mb-2';
        errorTitle.textContent = 'Error';

        const errorText = document.createElement('p');
        errorText.className = 'text-sm';
        errorText.textContent = sim.error_message;

        errorDiv.appendChild(errorTitle);
        errorDiv.appendChild(errorText);
        content.appendChild(errorDiv);
    }

    // Trades section
    const tradesSection = document.createElement('div');
    tradesSection.className = 'bg-gray-700 rounded-lg p-4';

    const tradesTitle = document.createElement('h4');
    tradesTitle.className = 'font-medium mb-3';
    tradesTitle.textContent = 'Recent Trades';
    tradesSection.appendChild(tradesTitle);

    if (trades.length === 0) {
        const noTrades = document.createElement('p');
        noTrades.className = 'text-gray-400 text-sm';
        noTrades.textContent = 'No trades yet';
        tradesSection.appendChild(noTrades);
    } else {
        const tableWrapper = document.createElement('div');
        tableWrapper.className = 'overflow-x-auto';

        const table = document.createElement('table');
        table.className = 'w-full text-sm';

        // Table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        headerRow.className = 'text-gray-400 border-b border-gray-600';

        ['Time', 'Action', 'Price', 'P&L'].forEach((text, i) => {
            const th = document.createElement('th');
            th.className = i >= 2 ? 'text-right py-2' : 'text-left py-2';
            th.textContent = text;
            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Table body
        const tbody = document.createElement('tbody');
        trades.forEach(t => {
            const row = document.createElement('tr');
            row.className = 'border-b border-gray-600/50';

            const timeCell = document.createElement('td');
            timeCell.className = 'py-2';
            timeCell.textContent = formatTime(t.created_at);

            const actionCell = document.createElement('td');
            actionCell.className = 'py-2';
            actionCell.textContent = t.action;

            const priceCell = document.createElement('td');
            priceCell.className = 'py-2 text-right';
            priceCell.textContent = `$${formatNumber(t.entry_price || t.exit_price || 0)}`;

            const pnlCell = document.createElement('td');
            pnlCell.className = `py-2 text-right ${(t.pnl || 0) >= 0 ? 'text-profit' : 'text-loss'}`;
            pnlCell.textContent = t.pnl ? `$${formatNumber(t.pnl)}` : '-';

            row.appendChild(timeCell);
            row.appendChild(actionCell);
            row.appendChild(priceCell);
            row.appendChild(pnlCell);
            tbody.appendChild(row);
        });

        table.appendChild(tbody);
        tableWrapper.appendChild(table);
        tradesSection.appendChild(tableWrapper);
    }

    content.appendChild(tradesSection);
}

// Create a detail section
function createDetailSection(title, items) {
    const section = document.createElement('div');
    section.className = 'bg-gray-700 rounded-lg p-4';

    const h4 = document.createElement('h4');
    h4.className = 'font-medium mb-3';
    h4.textContent = title;
    section.appendChild(h4);

    const container = document.createElement('div');
    container.className = 'space-y-2 text-sm';

    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'flex justify-between';

        const label = document.createElement('span');
        label.className = 'text-gray-400';
        label.textContent = item.label;

        const value = document.createElement('span');
        if (item.valueClass) {
            value.className = item.valueClass;
        }
        value.textContent = item.value;

        div.appendChild(label);
        div.appendChild(value);
        container.appendChild(div);
    });

    section.appendChild(container);
    return section;
}

// Utility functions
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return parseFloat(num).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatInterval(seconds) {
    if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h`;
    if (seconds >= 60) return `${Math.floor(seconds / 60)}m`;
    return `${seconds}s`;
}

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

function showSuccess(message) {
    showToast(message, 'success');
}

function showError(message) {
    showToast(message, 'error');
}

function showToast(message, type) {
    // Remove existing toasts
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast fixed bottom-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-600' : 'bg-red-600'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}
