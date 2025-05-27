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

# Load tokens from environment variables like TOKEN1, TOKEN2, ...
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
if not tokens:
    print(f"{Fore.RED}No tokens found in environment variables! Use TOKEN1, TOKEN2, etc.")
    sys.exit()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

status = "dnd"  # online/idle/dnd
custom_status = ".gg/rollbet"  # custom presence text

def validate_token(token):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    r = requests.get("https://canary.discord.com/api/v9/users/@me", headers=headers)
    if r.status_code != 200:
        return None
    return r.json()

async def send_webhook_message(session, content):
    if not WEBHOOK_URL:
        return
    try:
        async with session.post(WEBHOOK_URL, json={"content": content}) as resp:
            if resp.status != 204:
                print(f"{Fore.RED}[!] Failed to send webhook message, status code: {resp.status}")
    except Exception as e:
        print(f"{Fore.RED}[!] Exception sending webhook message: {e}")

async def heartbeat_loop(ws, interval):
    try:
        while True:
            await ws.send(json.dumps({"op": 1, "d": None}))
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass  # Expected on shutdown

async def onliner(token, session):
    userinfo = validate_token(token)
    if not userinfo:
        print(f"{Fore.RED}[x] Invalid token: {token[:6]}...")
        return

    username = userinfo["username"]
    discriminator = userinfo["discriminator"]

    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                start = json.loads(await ws.recv())
                heartbeat_interval = start["d"]["heartbeat_interval"] / 1000  # usually 40 sec

                heartbeat_task = asyncio.create_task(heartbeat_loop(ws, heartbeat_interval))

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

                print(f"{Fore.GREEN}[+] Online: {username}#{discriminator} ({userinfo['id']})")
                await send_webhook_message(session, f"[▶️ ONLINE] `{username}#{discriminator}` is now online.")

                # Stay online for 2 to 4 hours (7200 to 14400 seconds)
                online_time = random.randint(7200, 14400)
                await asyncio.sleep(online_time)

                print(f"{Fore.YELLOW}[-] {username}#{discriminator} going offline for a break...")
                await send_webhook_message(session, f"[😴 SLEEP] `{username}#{discriminator}` is sleeping for a bit.")

                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

                await ws.close()

                # Sleep offline for 1 to 3 minutes (60 to 180 seconds)
                offline_time = random.randint(60, 180)
                await asyncio.sleep(offline_time)

                print(f"{Fore.CYAN}[+] {username}#{discriminator} woke up after {offline_time} seconds.")
                await send_webhook_message(session, f"[☀️ WAKE UP] `{username}#{discriminator}` woke up after sleeping {offline_time} seconds.")

        except websockets.ConnectionClosed as e:
            print(f"{Fore.YELLOW}[!] Connection closed for {username}#{discriminator}: {e}. Reconnecting in 30s...")
            await send_webhook_message(session, f"[🔄 RECONNECT] `{username}#{discriminator}` connection closed ({e.code}). Reconnecting in 30 seconds.")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"{Fore.RED}[!] Error for {username}#{discriminator}: {e}. Retrying in 30s...")
            await send_webhook_message(session, f"[❌ ERROR] `{username}#{discriminator}`: {e} — retrying in 30 seconds.")
            await asyncio.sleep(30)

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for token in tokens:
            # Optional: staggered start (0-60s delay)
            stagger_delay = random.randint(0, 60)
            print(f"{Fore.BLUE}[i] Waiting {stagger_delay} seconds before starting token {token[:6]}...")
            await asyncio.sleep(stagger_delay)
            tasks.append(asyncio.create_task(onliner(token, session)))

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.RED}\n[!] Exiting... Goodbye!")
        sys.exit()
