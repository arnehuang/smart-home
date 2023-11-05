import asyncio
from kasa import Discover


async def discover_devices():
    devices = await Discover.discover()
    for addr, dev in devices.items():
        print(f"{dev.alias} @ {addr}")


# Custom exception handler that ignores specific RuntimeErrors
def ignore_eventloopclosed(exc, context):
    if not isinstance(exc, RuntimeError) or "Event loop is closed" not in str(exc):
        loop.default_exception_handler(context)


# Run the discovery
loop = asyncio.get_event_loop()
loop.set_exception_handler(ignore_eventloopclosed)
loop.run_until_complete(discover_devices())
loop.close()
