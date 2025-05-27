import os
import sys
import json
import asyncio
import random
import platform
import requests
import websockets
import aiohttp
from colorama import init, Fore
from datetime import datetime, timedelta

init(autoreset=True)

status = "dnd"
custom_status = ".gg/rollbet"

# Load tokens from environment
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
webhook_url = os.getenv("WEBHOOK_URL")

if not tokens:
    print(f"{Fore.RED}No tokens found in environment variables! Use TOKEN1, TOKEN2, etc.")
    sys.exit()

def validate_token(token):
    headers = {"Authorization": token, "Content-Type": "application/json"}
    r = requests.get("https://canary.discord.com/api/v9/users/@me", headers=headers)
    if r.status_code != 200:
        return None
    return r.json()

async def send_webhook(session, content):
    if not webhook_url:
        return
    try:
        await session.post(webhook_url, json={"content": content})
    except Exception as e:
        print(f"{Fore.RED}[!] Webhook error: {e}")

async def onliner(token, userinfo, session):
    username = f"{userinfo['username']}#{userinfo['discriminator']}"
    token_id = token[:6]

    while True:
        try:
            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                start = json.loads(await ws.recv())
                heartbeat_interval = start["d"]["heartbeat_interval"] / 1000  # Usually ~40s

                async def heartbeat():
                    while True:
                        await ws.send(json.dumps({"op": 1, "d": None}))
                        await asyncio.sleep(heartbeat_interval)

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

                now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                print(f"{Fore.GREEN}[+] Online: {username} ({token_id}) — {now}")
                await send_webhook(session, f"✅ `{username}` is now **online** at {now}.")

                # Stay online 2–4 hours
                uptime = random.randint(7200, 14400)
                await asyncio.sleep(uptime)

                print(f"{Fore.YELLOW}[-] {username} going offline for a bit...")
                await send_webhook(session, f"😴 `{username}` is going offline for a rest (was online for {uptime // 60} mins).")

                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                await ws.close()

                # Sleep 1–5 mins
                sleep_time = random.randint(60, 300)
                await asyncio.sleep(sleep_time)

                print(f"{Fore.CYAN}[☀️] {username} waking up after {sleep_time} seconds.")
                await send_webhook(session, f"☀️ `{username}` is back online after sleeping for {sleep_time} seconds.")

        except websockets.ConnectionClosed as e:
            print(f"{Fore.YELLOW}[!] Disconnected: {username} — {e}. Retrying in 30s.")
            await send_webhook(session, f"🔄 `{username}` was disconnected ({e.code}). Reconnecting in 30 seconds.")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"{Fore.RED}[!] Error with {username}: {e}")
            await send_webhook(session, f"❌ Error for `{username}`: {e}. Retrying in 30 seconds.")
            await asyncio.sleep(30)

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for token in tokens:
            userinfo = validate_token(token)
            if not userinfo:
                print(f"{Fore.RED}[x] Invalid token: {token[:10]}...")
                continue
            delay = random.randint(5, 30)
            print(f"{Fore.BLUE}[i] Staggering start for {userinfo['username']}#{userinfo['discriminator']} by {delay}s")
            await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(onliner(token, userinfo, session)))
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.RED}\n[!] Exiting... Goodbye!")
        sys.exit()
