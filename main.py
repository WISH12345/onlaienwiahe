import os
import sys
import json
import asyncio
import platform
import requests
import websockets
from colorama import init, Fore
from keep_alive import keep_alive  # Flask keep-alive script

init(autoreset=True)

status = "dnd"  # Options: "online", "idle", or "dnd"
custom_status = ".gg/rollbet"
webhook_url = os.getenv("WEBHOOK_URL")  # Webhook for logging

def send_webhook(message):
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"content": message})
    except Exception as e:
        print(f"{Fore.RED}[!] Webhook error: {e}")

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
    try:
        async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
            start = json.loads(await ws.recv())
            heartbeat_interval = start["d"]["heartbeat_interval"] / 1000

            async def heartbeat():
                while True:
                    try:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                    except Exception as e:
                        print(f"{Fore.RED}[!] Heartbeat error: {e}")
                        break
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

            online_msg = f"[+] Online: {userinfo['username']}#{userinfo['discriminator']} ({userinfo['id']})"
            print(f"{Fore.GREEN}{online_msg}")
            send_webhook(online_msg)

            while True:
                await ws.recv()

    except Exception as e:
        err_msg = f"[!] Error for {userinfo.get('username', '?')}#{userinfo.get('discriminator', '?')}: {e}"
        print(f"{Fore.RED}{err_msg}")
        send_webhook(err_msg)
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
            send_webhook(f"[x] Invalid token: {token[:10]}...")
            continue
        tasks.append(asyncio.create_task(onliner(token, userinfo)))
    await asyncio.gather(*tasks)

# Start Flask keep-alive server (for Railway/Replit)
keep_alive()

# Run the main async task
asyncio.run(run_all())
