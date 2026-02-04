/**
 * AI Trading Bot Dashboard
 * Auto-refresh logic and UI updates
 */

const REFRESH_INTERVAL = 30000; // 30 seconds
const API_BASE = '/api';

/**
 * Format currency value
 */
function formatCurrency(value, decimals = 2) {
    if (value === null || value === undefined) return '--';
    const num = parseFloat(value);
    if (isNaN(num)) return '--';
    return '$' + num.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * Format percentage value
 */
function formatPercent(value, includeSign = true) {
    if (value === null || value === undefined) return '--';
    const num = parseFloat(value);
    if (isNaN(num)) return '--';
    const sign = includeSign && num > 0 ? '+' : '';
    return sign + num.toFixed(2) + '%';
}

/**
 * Format timestamp to readable time
 */
function formatTime(timestamp) {
    if (!timestamp) return '--';
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return timestamp;
    }
}

/**
 * Get CSS class based on value sign
 */
function getValueClass(value) {
    const num = parseFloat(value);
    if (isNaN(num) || num === 0) return 'text-gray-400';
    return num > 0 ? 'text-profit' : 'text-loss';
}

/**
 * Get interpretation class
 */
function getInterpretationClass(interpretation) {
    const lower = (interpretation || '').toLowerCase();
    if (lower.includes('bullish')) return 'bullish';
    if (lower.includes('bearish')) return 'bearish';
    return 'neutral';
}

/**
 * Get Fear & Greed color class
 */
function getFearGreedClass(value) {
    if (value <= 25) return 'text-red-500';
    if (value <= 45) return 'text-orange-500';
    if (value <= 55) return 'text-gray-400';
    if (value <= 75) return 'text-green-400';
    return 'text-green-500';
}

/**
 * Create element with text content (safe from XSS)
 */
function createTextElement(tag, text, className = '') {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    return el;
}

/**
 * Clear and populate container safely
 */
function clearContainer(container) {
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
}

/**
 * Update status section
 */
function updateStatus(status) {
    if (!status) return;

    document.getElementById('run-name').textContent = status.run_name || 'Unknown';

    const modeBadge = document.getElementById('mode-badge');
    if (status.mode === 'forward_testing') {
        modeBadge.textContent = 'Paper Trading';
        modeBadge.className = 'ml-2 px-2 py-0.5 rounded text-xs font-medium bg-yellow-600';
    } else {
        modeBadge.textContent = 'Live';
        modeBadge.className = 'ml-2 px-2 py-0.5 rounded text-xs font-medium bg-green-600';
    }
}

/**
 * Update performance metrics
 */
function updateMetrics(metrics) {
    if (!metrics) return;

    document.getElementById('win-rate').textContent = formatPercent(metrics.win_rate, false);
    document.getElementById('win-rate').className = 'font-semibold ' + getValueClass(metrics.win_rate - 50);

    const pnlElement = document.getElementById('total-pnl');
    pnlElement.textContent = formatCurrency(metrics.total_pnl);
    pnlElement.className = 'font-semibold ' + getValueClass(metrics.total_pnl);

    document.getElementById('profit-factor').textContent =
        metrics.profit_factor !== null ? metrics.profit_factor.toFixed(2) : '--';

    document.getElementById('max-drawdown').textContent = formatCurrency(metrics.max_drawdown);

    document.getElementById('total-trades').textContent =
        `${metrics.winning_trades || 0}W / ${metrics.losing_trades || 0}L (${metrics.total_trades || 0})`;

    const streak = metrics.current_streak || 0;
    const streakElement = document.getElementById('current-streak');
    streakElement.textContent = streak === 0 ? 'None' :
        (streak > 0 ? `${streak} wins` : `${Math.abs(streak)} losses`);
    streakElement.className = getValueClass(streak);
}

/**
 * Update market data section (safe DOM manipulation)
 */
function updateMarketData(market) {
    const container = document.getElementById('market-data');
    clearContainer(container);

    if (!market || Object.keys(market).length === 0) {
        container.appendChild(createTextElement('p', 'No market data available', 'text-gray-500 text-sm'));
        return;
    }

    for (const [symbol, data] of Object.entries(market)) {
        if (data.error) {
            container.appendChild(createTextElement('div', `${symbol}: Error loading data`, 'text-gray-500 text-sm'));
            continue;
        }

        const row = document.createElement('div');
        row.className = 'flex justify-between items-center';

        const leftDiv = document.createElement('div');
        leftDiv.appendChild(createTextElement('span', symbol, 'font-semibold'));

        const rightDiv = document.createElement('div');
        rightDiv.className = 'text-right';
        rightDiv.appendChild(createTextElement('div', formatCurrency(data.price), 'font-semibold'));
        rightDiv.appendChild(createTextElement('div', formatPercent(data.price_change_24h_percent), 'text-sm ' + getValueClass(data.price_change_24h_percent)));

        row.appendChild(leftDiv);
        row.appendChild(rightDiv);
        container.appendChild(row);
    }
}

/**
 * Update Fear & Greed Index
 */
function updateFearGreed(data) {
    const valueEl = document.getElementById('fear-greed-value');
    const labelEl = document.getElementById('fear-greed-label');

    if (!data || data.error) {
        valueEl.textContent = '--';
        labelEl.textContent = 'Unknown';
        return;
    }

    valueEl.textContent = data.value;
    valueEl.className = 'font-bold text-lg ' + getFearGreedClass(data.value);
    labelEl.textContent = data.classification || 'Unknown';
}

/**
 * Update account balance
 */
function updateBalance(balance) {
    const balanceEl = document.getElementById('usd-balance');
    if (!balance || balance.error) {
        balanceEl.textContent = 'Unavailable';
        return;
    }
    balanceEl.textContent = formatCurrency(balance.usd_available);
}

/**
 * Close a position via API
 */
async function closePosition(symbol, positionId) {
    if (!confirm(`Close position for ${symbol}?`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/positions/close`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, position_id: positionId })
        });

        const result = await response.json();

        if (result.success) {
            alert(`Position closed!\nP&L: ${formatCurrency(result.pnl)}\nNew Balance: ${formatCurrency(result.new_balance)}`);
            fetchDashboardData(); // Refresh data
        } else {
            alert(`Failed to close position: ${result.error}`);
        }
    } catch (error) {
        console.error('Failed to close position:', error);
        alert('Failed to close position. Check console for details.');
    }
}

/**
 * Update positions section (safe DOM manipulation)
 */
function updatePositions(positions) {
    const container = document.getElementById('positions-container');
    clearContainer(container);

    if (!positions || positions.length === 0) {
        container.appendChild(createTextElement('p', 'No open positions', 'text-gray-500 text-sm'));
        return;
    }

    for (const pos of positions) {
        const card = document.createElement('div');
        card.className = 'bg-gray-700 rounded p-4 mb-3';

        // Header row with symbol and side badge
        const headerRow = document.createElement('div');
        headerRow.className = 'flex justify-between items-center mb-3';

        const symbolDiv = document.createElement('div');
        symbolDiv.className = 'flex items-center gap-2';
        symbolDiv.appendChild(createTextElement('span', pos.symbol, 'font-bold text-lg'));

        const sideBadge = document.createElement('span');
        sideBadge.className = 'text-xs px-2 py-1 rounded font-medium ' + (pos.side === 'buy' ? 'bg-green-600' : 'bg-red-600');
        sideBadge.textContent = pos.side === 'buy' ? 'LONG' : 'SHORT';
        symbolDiv.appendChild(sideBadge);

        if (pos.is_paper) {
            const paperBadge = document.createElement('span');
            paperBadge.className = 'text-xs px-2 py-1 rounded bg-yellow-600 font-medium';
            paperBadge.textContent = 'PAPER';
            symbolDiv.appendChild(paperBadge);
        }

        headerRow.appendChild(symbolDiv);
        card.appendChild(headerRow);

        // P&L Display - Prominent
        if (pos.unrealized_pnl !== null) {
            const pnlContainer = document.createElement('div');
            pnlContainer.className = 'bg-gray-800 rounded p-3 mb-3 text-center';

            const pnlLabel = document.createElement('div');
            pnlLabel.className = 'text-gray-400 text-xs uppercase tracking-wide mb-1';
            pnlLabel.textContent = 'If you close now';
            pnlContainer.appendChild(pnlLabel);

            const pnlValue = document.createElement('div');
            pnlValue.className = 'text-2xl font-bold ' + getValueClass(pos.unrealized_pnl);
            pnlValue.textContent = formatCurrency(pos.unrealized_pnl);
            pnlContainer.appendChild(pnlValue);

            // Calculate P&L percentage if we have entry price
            if (pos.avg_open_price > 0) {
                const positionValue = pos.avg_open_price * pos.quantity;
                const pnlPercent = (pos.unrealized_pnl / positionValue) * 100;
                const pnlPercentEl = document.createElement('div');
                pnlPercentEl.className = 'text-sm ' + getValueClass(pnlPercent);
                pnlPercentEl.textContent = formatPercent(pnlPercent);
                pnlContainer.appendChild(pnlPercentEl);
            }

            card.appendChild(pnlContainer);
        }

        // Details grid
        const grid = document.createElement('div');
        grid.className = 'grid grid-cols-2 gap-2 text-sm mb-3';

        // Quantity
        const qtyDiv = document.createElement('div');
        qtyDiv.appendChild(createTextElement('span', 'Quantity: ', 'text-gray-400'));
        qtyDiv.appendChild(document.createTextNode(pos.quantity.toFixed(6)));
        grid.appendChild(qtyDiv);

        // Entry price
        const entryDiv = document.createElement('div');
        entryDiv.appendChild(createTextElement('span', 'Entry: ', 'text-gray-400'));
        entryDiv.appendChild(document.createTextNode(formatCurrency(pos.avg_open_price)));
        grid.appendChild(entryDiv);

        // Current price
        const priceDiv = document.createElement('div');
        priceDiv.appendChild(createTextElement('span', 'Current: ', 'text-gray-400'));
        priceDiv.appendChild(document.createTextNode(formatCurrency(pos.current_price)));
        grid.appendChild(priceDiv);

        // Position value
        const valueDiv = document.createElement('div');
        valueDiv.appendChild(createTextElement('span', 'Value: ', 'text-gray-400'));
        valueDiv.appendChild(document.createTextNode(formatCurrency(pos.current_price * pos.quantity)));
        grid.appendChild(valueDiv);

        card.appendChild(grid);

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'w-full bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded transition-colors';
        closeBtn.textContent = 'Close Position';
        closeBtn.addEventListener('click', () => closePosition(pos.symbol, pos.position_id));
        card.appendChild(closeBtn);

        container.appendChild(card);
    }
}

/**
 * Update AI signals section (safe DOM manipulation)
 */
function updateAISignals(signals) {
    const container = document.getElementById('ai-signals');
    clearContainer(container);

    if (!signals || signals.length === 0) {
        container.appendChild(createTextElement('p', 'No AI signals recorded', 'text-gray-500 text-sm'));
        return;
    }

    for (const signal of signals) {
        const card = document.createElement('div');
        card.className = 'bg-gray-700 rounded p-4';

        // Header
        const header = document.createElement('div');
        header.className = 'flex flex-wrap justify-between items-start gap-2 mb-2';

        const leftHeader = document.createElement('div');
        leftHeader.className = 'flex items-center gap-2';
        leftHeader.appendChild(createTextElement('span', signal.symbol, 'font-semibold'));

        const interpClass = getInterpretationClass(signal.interpretation);
        const interpBadge = document.createElement('span');
        interpBadge.className = 'px-2 py-0.5 rounded text-sm font-medium ' +
            (interpClass === 'bullish' ? 'bg-green-600' : interpClass === 'bearish' ? 'bg-red-600' : 'bg-gray-600');
        interpBadge.textContent = signal.interpretation;
        leftHeader.appendChild(interpBadge);
        header.appendChild(leftHeader);

        header.appendChild(createTextElement('div', formatTime(signal.timestamp), 'text-sm text-gray-400'));
        card.appendChild(header);

        // Reasons
        const reasonsP = document.createElement('p');
        reasonsP.className = 'text-sm text-gray-300 line-clamp-3';
        reasonsP.textContent = signal.reasons;
        card.appendChild(reasonsP);

        // Provider
        card.appendChild(createTextElement('div', 'Provider: ' + signal.provider, 'mt-2 text-xs text-gray-500'));

        container.appendChild(card);
    }
}

/**
 * Update trades table (safe DOM manipulation)
 */
function updateTrades(trades) {
    const tbody = document.getElementById('trades-table');
    clearContainer(tbody);

    if (!trades || trades.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 6;
        cell.className = 'text-center py-4 text-gray-500';
        cell.textContent = 'No trades yet';
        row.appendChild(cell);
        tbody.appendChild(row);
        return;
    }

    for (const trade of trades) {
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-700 hover:bg-gray-750';

        // Time
        const timeCell = document.createElement('td');
        timeCell.className = 'py-2 px-2';
        timeCell.textContent = formatTime(trade.exit_time);
        row.appendChild(timeCell);

        // Symbol
        const symbolCell = document.createElement('td');
        symbolCell.className = 'py-2 px-2 font-medium';
        symbolCell.textContent = trade.symbol;
        row.appendChild(symbolCell);

        // Side
        const sideCell = document.createElement('td');
        sideCell.className = 'py-2 px-2';
        const sideSpan = document.createElement('span');
        sideSpan.className = trade.side === 'buy' ? 'text-green-400' : 'text-red-400';
        sideSpan.textContent = trade.side.toUpperCase();
        sideCell.appendChild(sideSpan);
        row.appendChild(sideCell);

        // Entry
        const entryCell = document.createElement('td');
        entryCell.className = 'py-2 px-2 text-right';
        entryCell.textContent = formatCurrency(trade.entry_price);
        row.appendChild(entryCell);

        // Exit
        const exitCell = document.createElement('td');
        exitCell.className = 'py-2 px-2 text-right';
        exitCell.textContent = formatCurrency(trade.exit_price);
        row.appendChild(exitCell);

        // P&L
        const pnlCell = document.createElement('td');
        pnlCell.className = 'py-2 px-2 text-right ' + getValueClass(trade.pnl);
        pnlCell.textContent = `${formatCurrency(trade.pnl)} (${formatPercent(trade.pnl_percent)})`;
        row.appendChild(pnlCell);

        tbody.appendChild(row);
    }
}

/**
 * Update last updated timestamp
 */
function updateTimestamp() {
    const now = new Date();
    document.getElementById('last-updated').textContent =
        'Updated: ' + now.toLocaleTimeString();
}

/**
 * Fetch all dashboard data
 */
async function fetchDashboardData() {
    try {
        const response = await fetch(`${API_BASE}/summary`);
        if (!response.ok) throw new Error('API request failed');

        const data = await response.json();

        updateStatus(data.status);
        updateMetrics(data.metrics);
        updateMarketData(data.market);
        updateFearGreed(data.fear_greed);
        updateBalance(data.balance);
        updatePositions(data.positions);
        updateAISignals(data.ai_history);
        updateTrades(data.trades);
        updateTimestamp();

    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
    }
}

/**
 * Initialize dashboard
 */
function init() {
    // Initial fetch
    fetchDashboardData();

    // Set up auto-refresh
    setInterval(fetchDashboardData, REFRESH_INTERVAL);

    console.log('Dashboard initialized. Refreshing every', REFRESH_INTERVAL / 1000, 'seconds.');
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);
