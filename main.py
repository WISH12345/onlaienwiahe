import os
import sys
import json
import time
import asyncio
import random
import platform
import requests
import websockets
import aiohttp
from colorama import init, Fore
from datetime import datetime, timezone

init(autoreset=True)

# Load tokens from environment (for Railway)
def get_tokens():
    tokens = []
    i = 1
    while True:
        token = os.getenv(f"TOKEN{i}")
        if not token:
            break
        tokens.append(token.strip())
        i += 1
    return tokens

tokens = get_tokens()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

status = "dnd"
custom_status = ".gg/rollbet"

def get_user_info(token):
    headers = {"Authorization": token}
    r = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
    if r.status_code == 200:
        return r.json()
    return None

async def send_webhook(session, message):
    if not WEBHOOK_URL:
        return
    try:
        payload = {"content": message}
        async with session.post(WEBHOOK_URL, json=payload) as resp:
            if resp.status != 204:
                print(f"{Fore.RED}[!] Webhook failed: HTTP {resp.status}")
    except Exception as e:
        print(f"{Fore.RED}[!] Webhook error: {e}")

async def presence_cycle(token, session):
    user = get_user_info(token)
    if not user:
        print(f"{Fore.RED}[x] Invalid token: {token[:10]}...")
        return

    username = f"{user['username']}#{user['discriminator']}"

    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                hello = json.loads(await ws.recv())
                heartbeat_interval = hello['d']['heartbeat_interval'] / 1000

                async def heartbeat():
                    while True:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                        print(f"{Fore.LIGHTMAGENTA_EX}[HB] Heartbeat sent for {username}")
                        await asyncio.sleep(heartbeat_interval * 0.9)

                hb = asyncio.create_task(heartbeat())

                auth = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "$os": platform.system(),
                            "$browser": "Chrome",
                            "$device": "Desktop"
                        },
                        "presence": {
                            "status": status,
                            "afk": False,
                            "activities": [
                                {
                                    "type": 4,
                                    "state": custom_status,
                                    "name": "Custom Status"
                                }
                            ]
                        }
                    }
                }

                await ws.send(json.dumps(auth))
                await send_webhook(session, f"[✅ ONLINE] {username} is now online.")
                print(f"{Fore.GREEN}[+] Online: {username}")

                uptime = random.randint(7200, 14400)  # 2 to 4 hours
                start_time = datetime.now(timezone.utc)
                await asyncio.sleep(uptime)

                # Offline period
                await send_webhook(session, f"[😴 SLEEP] {username} sleeping after {uptime // 60} minutes online.")
                print(f"{Fore.YELLOW}[-] {username} going offline for a break...")

                hb.cancel()
                try:
                    await hb
                except asyncio.CancelledError:
                    pass

                await ws.close()

                sleep_time = random.randint(60, 180)  # 1 to 3 min
                await asyncio.sleep(sleep_time)

                await send_webhook(session, f"[☀️ WAKE UP] {username} is back online after sleeping {sleep_time} seconds.")

        except websockets.ConnectionClosed as e:
            print(f"{Fore.YELLOW}[!] Connection closed for {username}. Reconnecting in 30s...")
            await send_webhook(session, f"[🔄 RECONNECT] {username} connection closed ({e.code}). Retrying...")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"{Fore.RED}[!] Error for {username}: {e}")
            await send_webhook(session, f"[❌ ERROR] {username}: {e}")
            await asyncio.sleep(30)

async def main():
    print(f"{Fore.LIGHTBLUE_EX}[+] Starting presence simulator for {len(tokens)} accounts.")
    async with aiohttp.ClientSession() as session:
        tasks = []
        for token in tokens:
            delay = random.randint(0, 30)
            await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(presence_cycle(token, session)))
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.RED}\n[!] Exiting... Goodbye!")
        sys.exit()
