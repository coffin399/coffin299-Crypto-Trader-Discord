async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update Status Badge
        const statusBadge = document.getElementById('bot-status');
        statusBadge.textContent = data.status;
        if (data.status === 'Running') {
            statusBadge.style.color = 'var(--success-color)';
            statusBadge.style.background = 'rgba(16, 185, 129, 0.2)';
        }

        // Update Balance
        const balanceDisplay = document.getElementById('balance-display');
        const balanceDetail = document.getElementById('balance-detail');

        let total = 0;
        let details = [];

        // Simple balance formatting
        if (data.balance) {
            // Check if balance has 'total' key (standardized structure)
            const assets = data.balance.total || data.balance;

            for (const [coin, amount] of Object.entries(assets)) {
                if (amount > 0) {
                    details.push(`${parseFloat(amount).toFixed(4)} ${coin}`);
                }
            }
            balanceDisplay.textContent = details.length > 0 ? details[0] : "0.00";

            // JPY Display
            if (data.total_jpy) {
                const jpyFormatted = new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(data.total_jpy);
                // Show other assets if any
                const otherAssets = details.slice(1).join(', ');
                balanceDetail.innerHTML = `${otherAssets ? otherAssets + '<br>' : ''} <span style="color: #a0a0a0; font-size: 0.9em;">Total Est: ${jpyFormatted}</span>`;
            } else {
                balanceDetail.textContent = details.slice(1).join(', ') || "No Assets";
            }
        }

        // Update Strategy Info
        document.getElementById('target-pair').textContent = data.target_pair || "---";

        const signalEl = document.getElementById('ai-signal');
        const rec = data.recommendation;

        if (rec) {
            signalEl.textContent = rec.action;
            signalEl.className = 'value'; // reset
            if (rec.action === 'BUY') signalEl.classList.add('signal-buy');
            if (rec.action === 'SELL') signalEl.classList.add('signal-sell');

            document.getElementById('ai-confidence').textContent = rec.confidence || "---";
        }

        // Update Logs
        if (data.logs && data.logs.length > 0) {
            const logList = document.getElementById('log-list');
            logList.innerHTML = ''; // Clear existing
            // Show last 20 logs reversed
            data.logs.slice().reverse().slice(0, 20).forEach(log => {
                const li = document.createElement('li');
                li.textContent = log;
                logList.appendChild(li);
            });
        }

        // Update Positions
        const posList = document.getElementById('positions-list');
        if (data.positions && data.positions.length > 0) {
            posList.innerHTML = '';
            data.positions.forEach(pos => {
                const tr = document.createElement('tr');
                const pnlClass = pos.pnl >= 0 ? 'pnl-green' : 'pnl-red';
                tr.innerHTML = `
                    <td>${pos.symbol}</td>
                    <td class="${pos.side === 'LONG' ? 'text-green' : 'text-red'}">${pos.side}</td>
                    <td>${pos.size}</td>
                    <td>${pos.entry_price.toFixed(4)}</td>
                    <td class="${pnlClass}">${pos.pnl.toFixed(2)}</td>
                `;
                posList.appendChild(tr);
            });
        } else {
            posList.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#666; padding: 1rem;">No open positions</td></tr>';
        }

    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// Poll every 5 seconds
// Poll every 5 seconds
setInterval(updateStatus, 5000);
updateStatus();

// MetaMask Connection
const connectBtn = document.getElementById('connect-wallet');

if (typeof window.ethereum !== 'undefined') {
    connectBtn.addEventListener('click', async () => {
        try {
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            const account = accounts[0];

            // Update button state
            connectBtn.innerHTML = `
                <i data-lucide="check-circle"></i>
                <span>${account.substring(0, 6)}...${account.substring(38)}</span>
            `;
            connectBtn.classList.add('connected');
            lucide.createIcons();

            console.log('Connected to MetaMask:', account);

            // Optional: Send address to backend if needed
            // fetch('/api/wallet/connect', { method: 'POST', body: JSON.stringify({ address: account }) });

        } catch (error) {
            console.error('User denied account access', error);
            alert('Failed to connect wallet: ' + error.message);
        }
    });

    // Check if already connected
    window.ethereum.request({ method: 'eth_accounts' }).then(accounts => {
        if (accounts.length > 0) {
            const account = accounts[0];
            connectBtn.innerHTML = `
                <i data-lucide="check-circle"></i>
                <span>${account.substring(0, 6)}...${account.substring(38)}</span>
            `;
            connectBtn.classList.add('connected');
            lucide.createIcons();
        }
    });
} else {
    connectBtn.style.display = 'none';
    console.log('MetaMask not installed');
}
