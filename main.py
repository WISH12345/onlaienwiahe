import os
import sys
import json
import asyncio
import platform
import requests
import websockets
from colorama import init, Fore
from keep_alive import keep_alive  # Make sure you also have keep_alive.py

init(autoreset=True)

status = "dnd"  # Options: "online", "idle", or "dnd"
custom_status = ".gg/rollbet"  # Text to show in custom status

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

async def onliner(token, userinfo):
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

            print(f"{Fore.GREEN}[+]{Fore.WHITE} Online: {userinfo['username']}#{userinfo['discriminator']} ({userinfo['id']})")

            while True:
                await ws.recv()
    except Exception as e:
        print(f"{Fore.RED}[!] Error for {userinfo['username']}#{userinfo['discriminator']}: {e}")
        await asyncio.sleep(5)
        await onliner(token, userinfo)

async def run_all():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

    tasks = []
    for token in tokens:
        userinfo = validate_token(token)
        if not userinfo:
            print(f"{Fore.RED}[x] Invalid token: {token[:10]}...")
            continue
        tasks.append(asyncio.create_task(onliner(token, userinfo)))
    await asyncio.gather(*tasks)

# Start Flask keep-alive server (for Railway/Replit)
keep_alive()

# Run the main async task
asyncio.run(run_all())
