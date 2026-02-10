import asyncio
import aiohttp
import os
import time
from aiogram import Bot
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SCAN_INTERVAL = 30  # seconds
MAX_AGE_MINUTES = 45
MIN_LIQUIDITY = 3000  # USD

DEX_ENDPOINTS = {
    "solana": "raydium",
    "ethereum": "uniswap",
    "bsc": "pancakeswap",
    "base": "baseswap",
    "arbitrum": "uniswap",
    "avalanche": "traderjoe"
}

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

seen_pairs = set()

def has_telegram(pair):
    socials = pair.get("info", {}).get("socials", [])
    for s in socials:
        if s.get("type") == "telegram":
            return s.get("url")
    return None

def is_new(pair):
    created = pair.get("pairCreatedAt")
    if not created:
        return False
    age = (time.time() * 1000 - created) / 60000
    return age <= MAX_AGE_MINUTES

async def scan_dex(session, chain, dex_id):
    url = f"https://api.dexscreener.com/latest/dex/pairs/{dex_id}"

    async with session.get(url) as resp:
        data = await resp.json()
        pairs = data.get("pairs", [])

        for pair in pairs:
            pair_id = pair.get("pairAddress")

            if not pair_id or pair_id in seen_pairs:
                continue

            if pair.get("chainId") != chain:
                continue

            if not is_new(pair):
                continue

            liquidity = pair.get("liquidity", {}).get("usd", 0)
            if liquidity < MIN_LIQUIDITY:
                continue

            telegram = has_telegram(pair)
            if not telegram:
                continue

            seen_pairs.add(pair_id)

            base = pair["baseToken"]
            name = base["name"]
            symbol = base["symbol"]

            msg = (
                f"🚀 <b>NEW TOKEN DETECTED</b>\n\n"
                f"<b>Name:</b> {name} ({symbol})\n"
                f"<b>Chain:</b> {chain.upper()}\n"
                f"<b>Liquidity:</b> ${int(liquidity):,}\n\n"
                f"✅ <b>Telegram Community Found</b>\n\n"
                f"🔗 <a href='{pair['url']}'>View on Dexscreener</a>\n"
                f"💬 <a href='{telegram}'>Join Telegram</a>\n\n"
                f"⚠️ DYOR — New Launch"
            )

            await bot.send_message(
                CHAT_ID,
                msg,
                disable_web_page_preview=True
            )

async def main():
    async with aiohttp.ClientSession() as session:
        while True:
            tasks = []

            for chain, dex_id in DEX_ENDPOINTS.items():
                tasks.append(scan_dex(session, chain, dex_id))

            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                print("Scan error:", e)

            await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
