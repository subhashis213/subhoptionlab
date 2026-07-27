const WebSocket = require('ws');
const ws = new WebSocket('wss://subhoptionlab.onrender.com/ws/live-market');
ws.on('open', () => {
    ws.send(JSON.stringify({ action: "subscribe", keys: ["NSE_FO|61599"] }));
    console.log("Subscribed to NSE_FO|61599. Waiting for data...");
});
ws.on('message', (data) => {
    console.log("Received:", data.toString());
    const msg = JSON.parse(data);
    if (msg.instrument_key === "NSE_FO|61599") {
        console.log("SUCCESS! Got data for 61599");
        process.exit(0);
    }
});
setTimeout(() => {
    console.log("Timeout");
    process.exit(1);
}, 10000);
