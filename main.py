import os
import sys
import json
import asyncio
import platform
import requests
import websockets
from colorama import init, Fore
from keep_alive import keep_alive  # Assumes you have keep_alive.py (for Replit/Railway uptime ping)

init(autoreset=True)

status = "dnd"  # "online", "idle", or "dnd"
custom_status = ".gg/rollbet"  # Custom status message

usertoken = os.getenv("TOKEN")
if not usertoken:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Please add a token inside Secrets.")
    sys.exit()

headers = {"Authorization": usertoken, "Content-Type": "application/json"}

validate = requests.get("https://canary.discord.com/api/v9/users/@me", headers=headers)
if validate.status_code != 200:
    print(f"{Fore.WHITE}[{Fore.RED}-{Fore.WHITE}] Your token might be invalid. Please check it again.")
    sys.exit()

userinfo = validate.json()
username = userinfo["username"]
discriminator = userinfo["discriminator"]
userid = userinfo["id"]

async def onliner(token, status):
    try:
        async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
            start = json.loads(await ws.recv())
            heartbeat_interval = start["d"]["heartbeat_interval"] / 1000  # in seconds

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

            # Keep the connection open
            while True:
                await ws.recv()
    except Exception as e:
        print(f"{Fore.YELLOW}[!] Connection error: {e}")
        await asyncio.sleep(5)

async def run_onliner():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")
    print(f"{Fore.WHITE}[{Fore.LIGHTGREEN_EX}+{Fore.WHITE}] Logged in as {Fore.LIGHTBLUE_EX}{username}#{discriminator} ({userid})")
    
    while True:
        await onliner(usertoken, status)

# Start Flask keep-alive server (if you're using Railway/Replit)
keep_alive()

# Start the bot
asyncio.run(run_onliner())
