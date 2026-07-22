import asyncio
from papertrade.router_markets import get_indices

async def main():
    indices = await get_indices(user={"id": "test"})
    print(indices)

asyncio.run(main())
