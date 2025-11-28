const statusIndicator = document.getElementById('status-indicator');
const totalJpyElement = document.getElementById('total-jpy');
const balanceList = document.getElementById('balance-list');
const positionsTableBody = document.querySelector('#positions-table tbody');
const logContainer = document.getElementById('log-container');

function updateDashboard() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            // Status
            statusIndicator.textContent = data.status;
            statusIndicator.style.color = data.status === 'Running' ? 'var(--success-color)' : 'var(--danger-color)';

            // Balance
            if (data.total_jpy !== undefined) {
                totalJpyElement.textContent = `¥${Math.floor(data.total_jpy).toLocaleString()}`;
            }

            balanceList.innerHTML = '';
            if (data.balance && data.balance.total) {
                for (const [coin, amount] of Object.entries(data.balance.total)) {
                    if (parseFloat(amount) > 0) {
                        const div = document.createElement('div');
                        div.className = 'balance-item';
                        div.innerHTML = `<span>${coin}</span><span>${parseFloat(amount).toFixed(4)}</span>`;
                        balanceList.appendChild(div);
                    }
                }
            }

            // Positions
            positionsTableBody.innerHTML = '';
            if (data.positions && data.positions.length > 0) {
                data.positions.forEach(pos => {
                    const row = document.createElement('tr');
                    const pnlClass = parseFloat(pos.pnl) >= 0 ? 'long' : 'short';
                    const sideClass = pos.side === 'LONG' ? 'long' : 'short';

                    row.innerHTML = `
                        <td>${pos.symbol}</td>
                        <td class="${sideClass}">${pos.side}</td>
                        <td>${pos.size}</td>
                        <td class="${pnlClass}">${parseFloat(pos.pnl).toFixed(2)} USD</td>
                    `;
                    positionsTableBody.appendChild(row);
                });
            } else {
                positionsTableBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color: var(--text-secondary);">No open positions</td></tr>';
            }

            // Logs
            logContainer.innerHTML = '';
            if (data.logs) {
                data.logs.slice().reverse().forEach(log => {
                    const div = document.createElement('div');
                    div.className = 'log-entry';

                    // Simple parsing for color
                    let contentClass = '';
                    if (log.includes('BUY')) contentClass = 'buy';
                    if (log.includes('SELL')) contentClass = 'sell';

                    // Extract time (HH:MM:SS)
                    const timeMatch = log.match(/\d{2}:\d{2}:\d{2}/);
                    const time = timeMatch ? timeMatch[0] : '';
                    const message = log.replace(time, '').trim();

                    div.innerHTML = `<span class="log-time">${time}</span><span class="${contentClass}">${message}</span>`;
                    logContainer.appendChild(div);
                });
            }
        })
        .catch(error => console.error('Error fetching status:', error));
}

// Update every 2 seconds
setInterval(updateDashboard, 2000);
updateDashboard();
