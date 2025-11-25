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
            // Assuming balance is a dict like {'BTC': 1.0, 'USDC': 1000}
            // For display, we might want to convert to JPY or USD total if we had prices
            // For now, just show the first non-zero or total count
            for (const [coin, amount] of Object.entries(data.balance)) {
                if (amount > 0) {
                    details.push(`${amount.toFixed(4)} ${coin}`);
                }
            }
            balanceDisplay.textContent = details.length > 0 ? details[0] : "0.00";
            balanceDetail.textContent = details.slice(1).join(', ') || "Assets";
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

    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// Poll every 5 seconds
setInterval(updateStatus, 5000);
updateStatus();
