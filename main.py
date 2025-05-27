import os
import sys
import json
import asyncio
import platform
import random
import requests
import websockets
from colorama import init, Fore
from keep_alive import keep_alive  # Make sure you also have keep_alive.py
import aiohttp

init(autoreset=True)

status = "dnd"  # Options: "online", "idle", or "dnd"
custom_status = ".gg/rollbet"  # Text to show in custom status

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    print(f"{Fore.RED}[!] No WEBHOOK_URL found in environment variables.")
    sys.exit()

def get_tokens_from_env():
    tokens = []
    i = 1
    while True:
        token = os.getenv(f"TOKEN{i}")
        if not token:
            break
        tokens.append(token.strip())  # Strips any \n or spaces
        i += 1
    return tokens

tokens = get_tokens_from_env()

if not tokens:
    print(f"{Fore.RED}No tokens found in environment variables! Use TOKEN1, TOKEN2, etc.")
    sys.exit()

def validate_token(token):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    r = requests.get("https://canary.discord.com/api/v9/users/@me", headers=headers)
    if r.status_code != 200:
        return None
    return r.json()

async def send_webhook_message(session, content):
    try:
        async with session.post(WEBHOOK_URL, json={"content": content}) as resp:
            if resp.status != 204:
                print(f"{Fore.RED}[!] Failed to send webhook message, status code: {resp.status}")
    except Exception as e:
        print(f"{Fore.RED}[!] Exception sending webhook message: {e}")

async def onliner(token, userinfo, session):
    try:
        async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
            start = json.loads(await ws.recv())
            heartbeat_interval = start["d"]["heartbeat_interval"] / 1000

            async def heartbeat():
                while True:
                    await ws.send(json.dumps({"op": 1, "d": None}))
                    await asyncio.sleep(heartbeat_interval)

            asyncio.create_task(heartbeat())

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

            username = userinfo['username']
            discriminator = userinfo['discriminator']
            user_id = userinfo['id']
            print(f"{Fore.GREEN}[+]{Fore.WHITE} Online: {username}#{discriminator} ({user_id})")
            await send_webhook_message(session, f"✅ Online: `{username}#{discriminator}` ({user_id})")

            online_time = random.randint(3600, 7200)  # 1-2 hours online
            await asyncio.sleep(online_time)

            print(f"{Fore.YELLOW}[-]{Fore.WHITE} Going offline: {username}#{discriminator} ({user_id})")
            await send_webhook_message(session, f"💤 Offline: `{username}#{discriminator}` ({user_id})")

            await ws.close()

            offline_time = random.randint(60, 180)  # 1-3 minutes offline
            await asyncio.sleep(offline_time)

            print(f"{Fore.CYAN}[+]{Fore.WHITE} Woke up: {username}#{discriminator} ({user_id})")
            await send_webhook_message(session, f"☀️ Woke up: `{username}#{discriminator}` ({user_id})")

            # Restart cycle
            await onliner(token, userinfo, session)

    except Exception as e:
        print(f"{Fore.RED}[!] Error for {userinfo['username']}#{userinfo['discriminator']}: {e}")
        await send_webhook_message(session, f"❌ Error for `{userinfo['username']}#{userinfo['discriminator']}`: {e}")
        await asyncio.sleep(5)
        await onliner(token, userinfo, session)

async def run_all():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for token in tokens:
            userinfo = validate_token(token)
            if not userinfo:
                print(f"{Fore.RED}[x] Invalid token: {token[:10]}...")
                continue
            tasks.append(asyncio.create_task(onliner(token, userinfo, session)))
        await asyncio.gather(*tasks)

# Start Flask keep-alive server (for Railway/Replit)
keep_alive()

# Run the main async task
asyncio.run(run_all())
