import os
import sys
import json
import asyncio
import platform
import random
import requests
import websockets
import aiohttp
from colorama import init, Fore

init(autoreset=True)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Collect tokens from TOKEN1, TOKEN2, ... environment variables
tokens = []
i = 1
while True:
    token = os.getenv(f"TOKEN{i}")
    if not token:
        break
    tokens.append(token)

if not tokens:
    print(f"{Fore.RED}No tokens found in environment variables TOKEN1, TOKEN2, etc.")
    sys.exit()

CUSTOM_STATUS = ".gg/rollbet"
STATUS = "dnd"  # online/dnd/idle

async def send_webhook_log(message: str):
    if not WEBHOOK_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                WEBHOOK_URL,
                json={"content": message},
                headers={"Content-Type": "application/json"},
            )
    except Exception as e:
        print(f"{Fore.RED}[Webhook error] {e}")

async def heartbeat(ws, interval, username):
    try:
        while True:
            await asyncio.sleep(interval / 1000)
            await ws.send(json.dumps({"op": 1, "d": None}))
    except asyncio.CancelledError:
        # Task cancelled - normal on disconnect
        pass
    except Exception as e:
        await send_webhook_log(f"[⚠️ HEARTBEAT ERROR] {username}: {e}")

async def simulate_presence(token):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    validate = requests.get("https://canary.discord.com/api/v9/users/@me", headers=headers)

    if validate.status_code != 200:
        print(f"{Fore.RED}Invalid token detected. Skipping...")
        return

    userinfo = validate.json()
    username = userinfo.get("username")
    discriminator = userinfo.get("discriminator")
    userid = userinfo.get("id")

    print(f"{Fore.GREEN}[+] Online: {username}#{discriminator} ({userid})")
    await send_webhook_log(f"[✅ ONLINE] {username}#{discriminator} ({userid}) is now online.")

    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                start = json.loads(await ws.recv())
                heartbeat_interval = start["d"]["heartbeat_interval"]

                heartbeat_task = asyncio.create_task(heartbeat(ws, heartbeat_interval, username))

                auth_payload = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "$os": platform.system(),
                            "$browser": "Chrome",
                            "$device": "Windows",
                        },
                        "presence": {"status": STATUS, "afk": False},
                    },
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
                                "id": "custom",
                            }
                        ],
                        "status": STATUS,
                        "afk": False,
                    },
                }
                await ws.send(json.dumps(cstatus))

                # Stay online for 5-10 minutes
                online_duration = random.randint(300, 600)
                await asyncio.sleep(online_duration)

                await send_webhook_log(f"[😴 SLEEP] {username}#{discriminator} is sleeping for a bit.")
                await ws.close()

                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

                # Sleep offline for 1-3 minutes
                sleep_duration = random.randint(60, 180)
                await asyncio.sleep(sleep_duration)

                await send_webhook_log(f"[☀️ WAKE UP] {username}#{discriminator} is back online after sleeping {sleep_duration} seconds.")

        except websockets.ConnectionClosed as e:
            print(f"{Fore.YELLOW}[!] Connection closed for {username}: {e}. Reconnecting in 30s...")
            await send_webhook_log(f"[🔄 RECONNECT] {username} connection closed ({e.code}). Reconnecting in 30 seconds.")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"{Fore.RED}[!] Error for {username}: {e} Retrying in 30s...")
            await send_webhook_log(f"[❌ ERROR] {username}#{discriminator}: {e} — retrying in 30 seconds.")
            await asyncio.sleep(30)

async def main():
    print(f"{Fore.WHITE}[{Fore.LIGHTGREEN_EX}+{Fore.WHITE}] Starting presence simulator for {len(tokens)} account(s)...")
    await asyncio.gather(*(simulate_presence(token) for token in tokens))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.RED}\n[!] Exiting... Goodbye!")
