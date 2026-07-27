import asyncio
import websockets
import json

async def test():
    uri = "wss://subhoptionlab.onrender.com/ws/live-market"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"action": "subscribe", "keys": ["NSE_FO|61599"]}))
        print("Subscribed to NSE_FO|61599. Waiting for data...")
        for _ in range(5):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print("Received:", msg)
                data = json.loads(msg)
                if data.get("instrument_key") == "NSE_FO|61599":
                    print("SUCCESS! Got data for 61599")
                    return
            except asyncio.TimeoutError:
                print("Timeout waiting for message")
                break
        print("Did not receive data for 61599")

asyncio.run(test())
