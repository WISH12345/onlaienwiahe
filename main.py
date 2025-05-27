import os
import sys
import json
import asyncio
import platform
import random
import aiohttp
import requests
import websockets
from colorama import init, Fore

init(autoreset=True)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TOKENS = [t.strip() for t in os.getenv("TOKENS", "").split("\n") if t.strip()]
CUSTOM_STATUS = ".gg/rollbet"
STATUS = "dnd"

if not TOKENS:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Please add tokens inside your .env file as 'TOKENS'.")
    sys.exit()

async def send_webhook_log(message):
    if not WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                WEBHOOK_URL,
                json={"content": message},
                headers={"Content-Type": "application/json"}
            )
    except Exception as e:
        print(f"[!] Failed to send webhook log: {e}")

async def heartbeat(ws, interval, username):
    try:
        while True:
            await asyncio.sleep(interval / 1000)
            await ws.send(json.dumps({"op": 1, "d": None}))
    except Exception:
        await send_webhook_log(f"[⚠️ DISCONNECTED] {username} lost connection. Attempting to reconnect...")

async def simulate_presence(token):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    validate = requests.get("https://canary.discord.com/api/v9/users/@me", headers=headers)

    if validate.status_code != 200:
        print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Invalid token detected. Skipping...")
        return

    userinfo = validate.json()
    username = userinfo.get("username")
    discriminator = userinfo.get("discriminator")
    userid = userinfo.get("id")

    await send_webhook_log(f"[✅ ONLINE] {username}#{discriminator} ({userid}) is now online.")

    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                start = json.loads(await ws.recv())
                heartbeat_interval = start['d']['heartbeat_interval']

                asyncio.create_task(heartbeat(ws, heartbeat_interval, username))

                auth_payload = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "$os": platform.system(),
                            "$browser": "Chrome",
                            "$device": "Windows"
                        },
                        "presence": {"status": STATUS, "afk": False},
                    }
                }

                await ws.send(json.dumps(auth_payload))

                cstatus = {
                    "op": 3,
                    "d": {
                        "since": 0,
                        "activities": [
                            {
                                "type": 4,
                                "state": CUSTOM_STATUS,
                                "name": "Custom Status",
                                "id": "custom"
                            }
                        ],
                        "status": STATUS,
                        "afk": False,
                    }
                }
                await ws.send(json.dumps(cstatus))

                # Keep session alive
                await asyncio.sleep(random.randint(300, 600))  # Online for 5-10 minutes

                await send_webhook_log(f"[😴 SLEEP] {username}#{discriminator} is sleeping.")
                await ws.close()

                sleep_time = random.randint(60, 180)  # Sleep for 1–3 minutes
                await asyncio.sleep(sleep_time)

                await send_webhook_log(f"[☀️ WAKE UP] {username}#{discriminator} is back online after {sleep_time} seconds.")

        except Exception as e:
            await send_webhook_log(f"[!] Error for {username}: {e}. Retrying in 30s...")
            await asyncio.sleep(30)

async def main():
    print(f"{Fore.WHITE}[{Fore.LIGHTGREEN_EX}+{Fore.WHITE}] Starting presence simulator for {len(TOKENS)} account(s)...")
    tasks = [simulate_presence(token) for token in TOKENS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
