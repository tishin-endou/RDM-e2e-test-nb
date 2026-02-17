#!/usr/bin/env python3
"""Verify HTTPS connection to WEKO using aiohttp."""

import aiohttp
import asyncio

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://192.168.168.167", timeout=aiohttp.ClientTimeout(total=30)) as resp:
            print("Status:", resp.status)

asyncio.get_event_loop().run_until_complete(main())
