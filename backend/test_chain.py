import asyncio
from dotenv import load_dotenv
load_dotenv()
from papertrade.upstox_guard import fetch_option_chain

async def main():
    chain = await fetch_option_chain("NSE_INDEX|Nifty Bank", "2026-07-23")
    print(type(chain))
    if isinstance(chain, list) and len(chain) > 0:
        print(chain[0])
    elif isinstance(chain, dict):
        print(list(chain.keys())[:5])
        
asyncio.run(main())
