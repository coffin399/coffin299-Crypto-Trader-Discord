// Discord-like App Logic

let currentChannel = 'trade-alerts';
let lastLogCount = 0;
let tradeHistory = []; // Store trade events locally for now, or fetch from server if available

function switchChannel(channelName) {
    currentChannel = channelName;
    document.getElementById('current-channel-name').textContent = channelName;

    // Update active class in sidebar
    document.querySelectorAll('.channel-item').forEach(item => {
        item.classList.remove('active');
        if (item.textContent.includes(channelName)) {
            item.classList.add('active');
        }
    });

    renderChannelContent();
}

function renderChannelContent() {
    const container = document.getElementById('chat-container');
    container.innerHTML = ''; // Clear current content

    if (currentChannel === 'trade-alerts') {
        renderTradeAlerts(container);
    } else if (currentChannel === 'logs') {
        renderLogs(container);
    } else if (currentChannel === 'config') {
        container.innerHTML = '<div class="message"><div class="message-content">Configuration view not implemented yet. Check config.yaml</div></div>';
    }

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function renderTradeAlerts(container) {
    if (tradeHistory.length === 0) {
        container.innerHTML = `
            <div class="message">
                <div class="message-avatar"></div>
                <div class="message-body">
                    <div class="message-header">
                        <span class="username">Coffin299 Bot</span>
                        <span class="timestamp">System</span>
                    </div>
                    <div class="message-content">No trades executed yet. Waiting for signals...</div>
                </div>
            </div>`;
        return;
    }

    tradeHistory.forEach(trade => {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message';

        const color = trade.side === 'BUY' ? '#3ba55c' : '#ed4245';

        msgDiv.innerHTML = `
            <div class="message-avatar"></div>
            <div class="message-body">
                <div class="message-header">
                    <span class="username">Coffin299 Bot</span>
                    <span class="timestamp">${trade.time}</span>
                </div>
                <div class="embed" style="border-left-color: ${color}">
                    <div class="embed-title">${trade.side} ${trade.symbol}</div>
                    <div class="embed-field">
                        <div class="embed-field-name">Price</div>
                        <div class="embed-field-value">${trade.price}</div>
                    </div>
                    <div class="embed-field">
                        <div class="embed-field-name">Amount</div>
                        <div class="embed-field-value">${trade.amount}</div>
                    </div>
                    <div class="embed-field">
                        <div class="embed-field-name">Reason</div>
                        <div class="embed-field-value">${trade.reason}</div>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(msgDiv);
    });
}

function renderLogs(container) {
    // We fetch logs from global state or API
    // For now, we use the logs we fetched in updateStatus
    if (!window.latestLogs) return;

    window.latestLogs.forEach(log => {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message';
        msgDiv.style.marginBottom = '4px'; // Compact logs

        // Simple log formatting
        let color = '#dcddde';
        if (log.includes('ERROR')) color = '#ed4245';
        if (log.includes('WARNING')) color = '#faa61a';
        if (log.includes('SUCCESS')) color = '#3ba55c';

        msgDiv.innerHTML = `
            <div class="message-content" style="color: ${color}; font-family: monospace; font-size: 12px;">
                ${log}
            </div>
        `;
        container.appendChild(msgDiv);
    });
}

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update Member List (Right Sidebar)
        updateMembers(data);

        // Update Logs
        window.latestLogs = data.logs || [];

        // Parse logs for "Trade Executed" events to populate tradeHistory (Hack since we don't have a DB endpoint yet)
        parseLogsForTrades(data.logs);

        // Re-render current channel if needed (or just append? For now re-render is safer but slower)
        // Optimization: Only re-render if data changed or just append new logs.
        // For simplicity in this demo: Re-render if channel is active.
        if (currentChannel === 'logs' && data.logs.length !== lastLogCount) {
            renderChannelContent();
            lastLogCount = data.logs.length;
        } else if (currentChannel === 'trade-alerts') {
            // Only re-render if history count changed
            // We can check length of tradeHistory vs rendered elements
            const renderedCount = document.getElementById('chat-container').children.length;
            if (tradeHistory.length > 0 && (renderedCount <= 1 && tradeHistory.length > 0 || renderedCount !== tradeHistory.length)) {
                renderChannelContent();
            }
        }

    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

function updateMembers(data) {
    // Bot Status
    const statusText = document.getElementById('bot-status-text');
    if (statusText) statusText.textContent = data.status;

    // Balance
    const balanceContainer = document.getElementById('balance-container');
    if (balanceContainer && data.balance) {
        let html = '';

        // Total JPY
        if (data.total_jpy) {
            html += `
                <div class="balance-card">
                    <div class="member-subtext">Total Est. Value</div>
                    <div class="member-name text-green">¥${Math.floor(data.total_jpy).toLocaleString()}</div>
                </div>`;
        }

        // Coins
        const balances = data.balance.total || {};
        for (const [coin, amount] of Object.entries(balances)) {
            if (parseFloat(amount) > 0) {
                html += `
                <div class="balance-card">
                    <div class="member-subtext">${coin}</div>
                    <div class="member-name">${parseFloat(amount).toFixed(4)}</div>
                </div>`;
            }
        }
        balanceContainer.innerHTML = html;
    }

    // Positions
    const posContainer = document.getElementById('positions-container');
    if (posContainer && data.positions) {
        if (data.positions.length === 0) {
            posContainer.innerHTML = '<div class="member-subtext" style="padding: 8px;">No open positions</div>';
        } else {
            let html = '';
            data.positions.forEach(pos => {
                const sideClass = pos.side === 'LONG' ? 'long' : 'short';
                const pnlClass = pos.pnl >= 0 ? 'text-green' : 'text-red';

                html += `
                <div class="position-card ${sideClass}">
                    <div class="member-name">${pos.symbol} <span style="font-size: 10px; opacity: 0.7">${pos.side}</span></div>
                    <div class="member-subtext">Size: ${pos.size}</div>
                    <div class="member-subtext">Entry: ${pos.entry_price}</div>
                    <div class="member-subtext ${pnlClass}">PnL: ${pos.pnl.toFixed(2)}</div>
                </div>`;
            });
            posContainer.innerHTML = html;
        }
    }
}

function parseLogsForTrades(logs) {
    // Look for "EXECUTING COPY TRADE: SIDE PAIR @ PRICE (REASON)"
    // Example: "EXECUTING COPY TRADE: BUY ETH/USDC @ 3000 (Copying 2/3...)"
    // Or "Trade Executed: {...}"

    // We clear and rebuild history from logs to avoid duplicates for this simple implementation
    // In a real app, we'd append unique IDs.

    const newHistory = [];
    const regex = /EXECUTING COPY TRADE: (BUY|SELL) (\S+) @ ([\d.]+) \((.*)\)/;

    logs.forEach(log => {
        const match = log.match(regex);
        if (match) {
            // Extract timestamp from log line start "YYYY-MM-DD HH:MM:SS"
            const timeMatch = log.match(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/);
            const time = timeMatch ? timeMatch[0] : 'Unknown Time';

            newHistory.push({
                time: time,
                side: match[1],
                symbol: match[2],
                price: match[3],
                amount: "0.01", // Mock amount as it's not always in that specific log line
                reason: match[4]
            });
        }
    });

    tradeHistory = newHistory;
}

// Initial Load
renderChannelContent();
setInterval(updateStatus, 2000); // Poll every 2 seconds
updateStatus();
