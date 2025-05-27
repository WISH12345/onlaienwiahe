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

init(autoreset=True)

status = "dnd"  # online, idle, dnd
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

async def onliner(token, userinfo):
    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                seq = None  # sequence number

                # Receive Hello event
                hello_msg = json.loads(await ws.recv())
                heartbeat_interval = hello_msg["d"]["heartbeat_interval"] / 1000

                async def heartbeat():
                    while True:
                        payload = {"op": 1, "d": seq}
                        await ws.send(json.dumps(payload))
                        print(f"{Fore.CYAN}[{userinfo['username']}] Heartbeat sent with seq {seq}")
                        await asyncio.sleep(heartbeat_interval)

                hb_task = asyncio.create_task(heartbeat())

                # Send Identify payload
                identify = {
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
                            "activities": [{
                                "type": 4,
                                "state": custom_status,
                                "name": "Custom Status"
                            }]
                        }
                    }
                }
                await ws.send(json.dumps(identify))
                print(f"{Fore.GREEN}[+]{Fore.WHITE} Online: {userinfo['username']}#{userinfo['discriminator']} ({userinfo['id']})")

                # Stay connected and process incoming messages
                online_time = random.randint(3600, 7200)
                print(f"{Fore.YELLOW}[{userinfo['username']}] Staying online for {online_time} seconds.")

                end_time = asyncio.get_event_loop().time() + online_time
                while True:
                    if asyncio.get_event_loop().time() > end_time:
                        print(f"{Fore.MAGENTA}[{userinfo['username']}] Going offline now (closing websocket).")
                        hb_task.cancel()
                        await ws.close()
                        break

                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=heartbeat_interval*2)
                    except asyncio.TimeoutError:
                        print(f"{Fore.RED}[{userinfo['username']}] No message from server, reconnecting...")
                        hb_task.cancel()
                        await ws.close()
                        break

                    msg_json = json.loads(msg)
                    op = msg_json.get("op")
                    t = msg_json.get("t")
                    seq = msg_json.get("s") or seq

                    # Handle Heartbeat ACK
                    if op == 11:
                        print(f"{Fore.CYAN}[{userinfo['username']}] Heartbeat ACK received.")

                    # You can handle other events if needed (e.g. READY, RESUMED)

                # Offline time 1 to 3 minutes
                offline_time = random.randint(60, 180)
                print(f"{Fore.BLUE}[{userinfo['username']}] Offline for {offline_time} seconds.")
                await asyncio.sleep(offline_time)

        except Exception as e:
            print(f"{Fore.RED}[!] Error for {userinfo['username']}#{userinfo['discriminator']}: {e}")
            await asyncio.sleep(5)

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

keep_alive()
asyncio.run(run_all())
