import os
import sys
import json
import asyncio
import platform
import random
import requests
import websockets
from colorama import init, Fore

init(autoreset=True)

status = "dnd"  # online/dnd/idle
custom_status = ".gg/rollbet"  # Custom Status

# Load tokens TOKEN1, TOKEN2, TOKEN3 ...
tokens = []
for i in range(1, 5):
    token = os.getenv(f"TOKEN{i}")
    if token:
        tokens.append(token)

if not tokens:
    print(f"{Fore.RED}[!] No tokens found in environment variables TOKEN1, TOKEN2, ...")
    sys.exit()

async def onliner(token, index):
    token_short = token[:6]
    while True:
        try:
            print(f"{Fore.CYAN}[{index}] Validating token {token_short}...")
            headers = {"Authorization": token, "Content-Type": "application/json"}
            validate = requests.get("https://canary.discordapp.com/api/v9/users/@me", headers=headers)
            if validate.status_code != 200:
                print(f"{Fore.RED}[{index}] Token {token_short} invalid, skipping.")
                return

            userinfo = validate.json()
            username = userinfo.get("username", "Unknown")
            discriminator = userinfo.get("discriminator", "0000")

            print(f"{Fore.GREEN}[{index}] Connecting websocket for {username}#{discriminator} ({token_short})...")
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                start = json.loads(await ws.recv())
                heartbeat_interval = start["d"]["heartbeat_interval"]
                print(f"{Fore.BLUE}[{index}] Heartbeat interval: {heartbeat_interval} ms")

                auth = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "$os": platform.system(),
                            "$browser": "Google Chrome",
                            "$device": platform.system(),
                        },
                        "presence": {"status": status, "afk": False},
                    },
                }
                await ws.send(json.dumps(auth))
                print(f"{Fore.GREEN}[{index}] Sent authentication payload.")

                cstatus = {
                    "op": 3,
                    "d": {
                        "since": 0,
                        "activities": [
                            {
                                "type": 4,
                                "state": custom_status,
                                "name": "Custom Status",
                                "id": "custom",
                            }
                        ],
                        "status": status,
                        "afk": False,
                    },
                }
                await ws.send(json.dumps(cstatus))
                print(f"{Fore.GREEN}[{index}] Sent custom status payload.")

                online_payload = {"op": 1, "d": None}

                print(f"{Fore.LIGHTGREEN_EX}[{index}] {username}#{discriminator} ({token_short}) is now online.")
                
                # Start sending heartbeats repeatedly every heartbeat_interval ms
                async def heartbeat_loop():
                    while True:
                        await asyncio.sleep(heartbeat_interval / 1000)
                        await ws.send(json.dumps(online_payload))
                        print(f"{Fore.LIGHTBLUE_EX}[{index}] Heartbeat sent.")

                heartbeat_task = asyncio.create_task(heartbeat_loop())

                # Stay online for random time between 8 and 11 hours (28800 - 39600 seconds)
                online_time = random.randint(28800, 39600)
                print(f"{Fore.YELLOW}[{index}] Staying online for {online_time} seconds.")
                await asyncio.sleep(online_time)

                print(f"{Fore.MAGENTA}[{index}] Going offline for a break.")
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

                await ws.close()

                # Sleep offline for random 2 to 4 minutes
                offline_time = random.randint(120, 240)
                print(f"{Fore.CYAN}[{index}] Sleeping offline for {offline_time} seconds.")
                await asyncio.sleep(offline_time)

                print(f"{Fore.GREEN}[{index}] Woke up, reconnecting now...")

        except websockets.ConnectionClosed as e:
            print(f"{Fore.YELLOW}[{index}] Connection closed: {e}. Reconnecting in 30 seconds...")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"{Fore.RED}[{index}] Error: {e}. Retrying in 30 seconds...")
            await asyncio.sleep(30)


async def main():
    tasks = []
    for idx, token in enumerate(tokens, 1):
        stagger = random.randint(0, 20)
        print(f"{Fore.BLUE}[i] Waiting {stagger}s before starting token {idx} ({token[:6]})...")
        await asyncio.sleep(stagger)
        tasks.append(asyncio.create_task(onliner(token, idx)))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.RED}\n[!] Exiting... Goodbye!")
        sys.exit()
