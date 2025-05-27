import os
import sys
import json
import asyncio
import platform
import random
import websockets
import aiohttp
from datetime import datetime
from colorama import init, Fore

init(autoreset=True)

# Environment token and webhook loader
def get_tokens_from_env():
    tokens = []
    i = 1
    while True:
        token = os.getenv(f"TOKEN{i}")
        if not token:
            break
        tokens.append(token.strip())
        i += 1
    return tokens

tokens = get_tokens_from_env()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

status = "dnd"
custom_status = ".gg/rollbet"

# Send messages to Discord webhook
async def send_webhook_log(session, content):
    if not WEBHOOK_URL:
        return
    try:
        payload = {"content": content}
        async with session.post(WEBHOOK_URL, json=payload) as resp:
            if resp.status not in [200, 204]:
                print(f"{Fore.RED}[!] Webhook failed: {resp.status}")
    except Exception as e:
        print(f"{Fore.RED}[!] Webhook error: {e}")

# Keep a token online with sleep/wake cycle
async def simulate_presence(token):
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                    hello_payload = json.loads(await ws.recv())
                    heartbeat_interval = hello_payload["d"]["heartbeat_interval"] / 1000

                    # Send heartbeat every interval
                    async def heartbeat():
                        try:
                            while True:
                                await ws.send(json.dumps({"op": 1, "d": None}))
                                print(f"{Fore.LIGHTMAGENTA_EX}[HB] Sent heartbeat for {token[:6]}")
                                await asyncio.sleep(heartbeat_interval)
                        except asyncio.CancelledError:
                            return

                    heartbeat_task = asyncio.create_task(heartbeat())

                    # Authenticate and go online
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
                    print(f"{Fore.GREEN}[+] Token {token[:6]} is now online.")
                    await send_webhook_log(session, f"[✅ ONLINE] Token `{token[:6]}...` is now online at {datetime.utcnow().strftime('%H:%M:%S UTC')}.")

                    # Online uptime: 2–4 hours
                    uptime = random.randint(7200, 14400)
                    await asyncio.sleep(uptime)

                    print(f"{Fore.YELLOW}[-] Token {token[:6]} going offline for a break.")
                    await send_webhook_log(session, f"[😴 SLEEP] Token `{token[:6]}...` sleeping for a bit after {uptime // 60} minutes.")

                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass

                    await ws.close()

                    # Sleep offline: 1–3 minutes
                    downtime = random.randint(60, 180)
                    await asyncio.sleep(downtime)

                    print(f"{Fore.CYAN}[+] Token {token[:6]} waking up after {downtime} seconds.")
                    await send_webhook_log(session, f"[☀️ WAKE UP] Token `{token[:6]}...` woke up after {downtime} seconds.")

            except websockets.ConnectionClosed as e:
                print(f"{Fore.YELLOW}[!] Connection closed for {token[:6]}: {e}. Retrying...")
                await send_webhook_log(session, f"[🔄 RECONNECT] Token `{token[:6]}...` connection closed ({e.code}). Reconnecting in 30s.")
                await asyncio.sleep(30)

            except Exception as e:
                print(f"{Fore.RED}[!] Error for {token[:6]}: {e}. Retrying...")
                await send_webhook_log(session, f"[❌ ERROR] Token `{token[:6]}...`: {e} — retrying in 30 seconds.")
                await asyncio.sleep(30)

# Run all tokens with staggered start
async def main():
    print(f"{Fore.WHITE}[{Fore.LIGHTGREEN_EX}+{Fore.WHITE}] Starting simulator for {len(tokens)} account(s)...")

    tasks = []
    for token in tokens:
        delay = random.randint(10, 60)
        print(f"{Fore.BLUE}[~] Stagger delay of {delay}s before launching token {token[:6]}...")
        await asyncio.sleep(delay)
        tasks.append(asyncio.create_task(simulate_presence(token)))

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.RED}\n[!] Exiting... Goodbye!")
        sys.exit()
