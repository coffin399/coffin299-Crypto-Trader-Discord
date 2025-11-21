// Connect to WebSocket
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws`;
const ws = new WebSocket(wsUrl);

// Chart Setup
const chartContainer = document.getElementById('chart');
const chart = LightweightCharts.createChart(chartContainer, {
    layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#a0a0a0',
    },
    grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
    },
    width: chartContainer.clientWidth,
    height: 400,
    timeScale: {
        timeVisible: true,
        secondsVisible: false,
    },
});

const candleSeries = chart.addCandlestickSeries({
    upColor: '#00ff9d',
    downColor: '#ff4d4d',
    borderVisible: false,
    wickUpColor: '#00ff9d',
    wickDownColor: '#ff4d4d',
});

// Resize Observer
new ResizeObserver(entries => {
    if (entries.length === 0 || entries[0].target !== chartContainer) { return; }
    const newRect = entries[0].contentRect;
    chart.applyOptions({ width: newRect.width, height: newRect.height });
}).observe(chartContainer);

// WebSocket Handlers
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'status') {
        updateStatus(data.payload);
    } else if (data.type === 'candle') {
        candleSeries.update(data.payload);
    } else if (data.type === 'trade') {
        addTrade(data.payload);
    }
};

function updateStatus(status) {
    document.getElementById('total-value').innerText = `¥${status.total_value_jpy.toLocaleString()}`;
    
    const pnlElement = document.getElementById('pnl');
    const pnl = status.total_change_jpy;
    pnlElement.innerText = `${pnl >= 0 ? '+' : ''}¥${pnl.toLocaleString()}`;
    pnlElement.className = `sub-value ${pnl >= 0 ? 'positive' : 'negative'}`;
}

function addTrade(trade) {
    const list = document.getElementById('trade-list');
    const item = document.createElement('div');
    item.className = 'trade-item';
    item.innerHTML = `
        <div class="trade-info">
            <span class="trade-type ${trade.side === 'BUY' ? 'trade-buy' : 'trade-sell'}">${trade.side}</span>
            <span>${trade.symbol}</span>
            <span>@ ${trade.price}</span>
        </div>
        <div class="trade-time">${new Date().toLocaleTimeString()}</div>
    `;
    list.insertBefore(item, list.firstChild);
}
