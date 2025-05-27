import os
import sys
import json
import asyncio
import platform
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

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    print(f"{Fore.RED}[!] No WEBHOOK_URL found in environment variables.")
    sys.exit()

async def send_webhook_message(session, content):
    try:
        async with session.post(WEBHOOK_URL, json={"content": content}) as resp:
            if resp.status != 204:
                print(f"{Fore.RED}[!] Failed to send webhook message, status code: {resp.status}")
    except Exception as e:
        print(f"{Fore.RED}[!] Exception sending webhook message: {e}")

async def onliner(token, session, index):
    token_short = token[:6]
    while True:
        try:
            # Validate token before connecting
            headers = {"Authorization": token, "Content-Type": "application/json"}
            validate = requests.get("https://canary.discordapp.com/api/v9/users/@me", headers=headers)
            if validate.status_code != 200:
                print(f"{Fore.RED}[!] Token {token_short} invalid, skipping.")
                await send_webhook_message(session, f"❌ Token `{token_short}...` invalid, skipping.")
                return

            userinfo = validate.json()
            username = userinfo.get("username", "Unknown")
            discriminator = userinfo.get("discriminator", "0000")

            async with websockets.connect("wss://gateway.discord.gg/?v=9&encoding=json") as ws:
                start = json.loads(await ws.recv())
                heartbeat_interval = start["d"]["heartbeat_interval"]

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

                online_payload = {"op": 1, "d": None}

                print(f"{Fore.GREEN}[+] [{index}] {username}#{discriminator} ({token_short}) is now online.")
                await send_webhook_message(session, f"✅ Token `{token_short}...` ({username}#{discriminator}) is now online.")

                # Send heartbeat once per original style (after heartbeat interval)
                await asyncio.sleep(heartbeat_interval / 1000)
                await ws.send(json.dumps(online_payload))

                # Stay online for random time (e.g. 1 to 2 hours)
                online_time = random.randint(28800, 39600)
                await asyncio.sleep(online_time)

                print(f"{Fore.YELLOW}[-] [{index}] {username}#{discriminator} ({token_short}) going offline for a break.")
                await send_webhook_message(session, f"😴 Token `{token_short}...` ({username}#{discriminator}) is going offline for a break.")

                await ws.close()

                # Sleep offline for random 1 to 3 minutes
                offline_time = random.randint(120, 240)
                await asyncio.sleep(offline_time)

                print(f"{Fore.CYAN}[+] [{index}] {username}#{discriminator} ({token_short}) woke up after {offline_time} seconds.")
                await send_webhook_message(session, f"☀️ Token `{token_short}...` ({username}#{discriminator}) woke up after {offline_time} seconds.")

        except websockets.ConnectionClosed as e:
            print(f"{Fore.YELLOW}[!] [{index}] Connection closed for token {token_short}: {e}. Reconnecting in 30 seconds...")
            await send_webhook_message(session, f"🔄 Token `{token_short}...` connection closed ({e.code}). Reconnecting in 30 seconds.")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"{Fore.RED}[!] [{index}] Error for token {token_short}: {e}. Retrying in 30 seconds...")
            await send_webhook_message(session, f"❌ Token `{token_short}...` error: {e} — retrying in 30 seconds.")
            await asyncio.sleep(30)

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, token in enumerate(tokens, 1):
            stagger = random.randint(0, 20)
            print(f"{Fore.BLUE}[i] Waiting {stagger}s before starting token {idx} ({token[:6]})...")
            await asyncio.sleep(stagger)
            tasks.append(asyncio.create_task(onliner(token, session, idx)))
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{Fore.RED}\n[!] Exiting... Goodbye!")
        sys.exit()
