import asyncio
import json
import platform
import random
import sys
import os
from datetime import datetime, timezone

import websockets
import aiohttp
import requests
from colorama import init, Fore

init(autoreset=True)

# Load tokens from environment
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

if not tokens:
    print(f"{Fore.RED}[x] No tokens found in environment (TOKEN1, TOKEN2, etc.)")
    sys.exit(1)

if not WEBHOOK_URL:
    print(f"{Fore.RED}[x] WEBHOOK_URL not set")
    sys.exit(1)

status = "dnd"
custom_status = ".gg/rollbet"

def get_user_info(token):
    try:
        headers = {"Authorization": token}
        r = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# Send a webhook message with timestamp
async def send_webhook_log(session, message):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    payload = {"content": f"{message}\n🕒 {now}"}
    try:
        async with session.post(WEBHOOK_URL, json=payload) as resp:
            if resp.status != 204:
                print(f"{Fore.RED}[!] Webhook failed: status {resp.status}")
    except Exception as e:
        print(f"{Fore.RED}[!] Webhook error: {e}")

async def simulate_presence(token, session, username_display):
    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                start = json.loads(await ws.recv())
                heartbeat_interval = start["d"]["heartbeat_interval"] / 1000

                async def heartbeat():
                    while True:
                        jitter = random.uniform(-0.05, 0.05)
                        await ws.send(json.dumps({"op": 1, "d": None}))
                        await asyncio.sleep(heartbeat_interval * (1 + jitter))

                heartbeat_task = asyncio.create_task(heartbeat())

                auth_payload = {
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

                await ws.send(json.dumps(auth_payload))
                print(f"{Fore.GREEN}[+] {username_display} is now online.")
                await send_webhook_log(session, f"[✅ ONLINE] {username_display} is now online.")

                uptime = random.randint(28800, 39600)
                await asyncio.sleep(uptime)

                await send_webhook_log(session, f"[😴 SLEEP] {username_display} is sleeping for a bit.")
                print(f"{Fore.YELLOW}[-] {username_display} going offline.")

                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                await ws.close()

                sleep_duration = random.randint(120, 360)
                await asyncio.sleep(sleep_duration)

                await send_webhook_log(session, f"[☀️ WAKE UP] {username_display} is back online after sleeping {sleep_duration} seconds.")

        except websockets.ConnectionClosed as e:
            print(f"{Fore.YELLOW}[!] Connection closed for {username_display}: {e}. Reconnecting in 30s...")
            await send_webhook_log(session, f"[🔄 RECONNECT] {username_display} connection closed ({e.code}). Reconnecting in 30 seconds.")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"{Fore.RED}[!] Error for {username_display}: {e}")
            await send_webhook_log(session, f"[❌ ERROR] {username_display}: {e} — retrying in 30 seconds.")
            await asyncio.sleep(30)

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for token in tokens:
            user = get_user_info(token)
            username_display = f"{user['username']}#{user['discriminator']}" if user else f"{token[:6]}..."
            delay = random.randint(0, 60)
            print(f"{Fore.BLUE}[i] Waiting {delay}s before starting {username_display}...")
            await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(simulate_presence(token, session, username_display)))
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        print(f"{Fore.WHITE}[{Fore.LIGHTGREEN_EX}+{Fore.WHITE}] Starting presence simulator for {len(tokens)} account(s)...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.RED}\n[!] Exiting... Goodbye!")
