import os
import sys
import json
import asyncio
import random
import platform
import requests
import websockets
from colorama import init, Fore
from keep_alive import keep_alive

init(autoreset=True)

status = "dnd"
custom_status = ".gg/rollbet"

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

def validate_token(token):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    r = requests.get("https://canary.discord.com/api/v9/users/@me", headers=headers)
    if r.status_code != 200:
        return None
    return r.json()

async def simulate_presence(token, userinfo):
    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                start = json.loads(await ws.recv())
                heartbeat_interval = start["d"]["heartbeat_interval"] / 1000

                async def heartbeat():
                    while True:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                        await asyncio.sleep(heartbeat_interval)

                asyncio.create_task(heartbeat())

                payload = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "$os": "Windows",
                            "$browser": "Discord Client",
                            "$device": "Discord Client"
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

                await ws.send(json.dumps(payload))
                print(f"{Fore.GREEN}[+]{Fore.WHITE} Online: {userinfo['username']}#{userinfo['discriminator']}")

                # Stay online for 1 to 3 hours
                online_time = random.randint(3600, 10800)
                await asyncio.sleep(online_time)

                print(f"{Fore.YELLOW}[~]{Fore.WHITE} {userinfo['username']} going offline for rest.")

                # Disconnect
                await ws.close()

                # Rest for 2 to 5 minutes
                offline_time = random.randint(120, 300)
                await asyncio.sleep(offline_time)

        except Exception as e:
            print(f"{Fore.RED}[!] Error for {userinfo['username']}: {e}")
            await asyncio.sleep(60)

async def run_all():
    tasks = []
    for token in tokens:
        userinfo = validate_token(token)
        if not userinfo:
            print(f"{Fore.RED}[x] Invalid token: {token[:10]}...")
            continue
        await asyncio.sleep(random.randint(1, 10))  # stagger starts
        tasks.append(asyncio.create_task(simulate_presence(token, userinfo)))
    await asyncio.gather(*tasks)

keep_alive()
asyncio.run(run_all())
