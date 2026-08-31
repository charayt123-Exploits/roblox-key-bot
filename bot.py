import discord
from discord.ext import commands
from aiohttp import web
import datetime
import uuid
import json
import os
import asyncio

# --- CONFIGURATION ---
PREFIX = "!"
BOT_TOKEN = "MTU0Mzk3MzA5NjE1MzY4MjA5MQ.G-3abk.7iFV_H47EBhW6szB_6RZvrmLT89wLIqXbDw9Ok" 
API_PORT = 8080
KEYS_FILE = "keys.json"

# --- INTENTS ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_keys(keys_data):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys_data, f, indent=4)

@bot.command(name="DM")
async def generate_key(ctx, duration_str: str = None):
    if not duration_str:
        await ctx.send("Usage: `!DM <1H|5H|12H|24H>`")
        return

    durations = {"1H": 1, "5H": 5, "12H": 12, "24H": 24}
    unit = duration_str.upper()
    
    if unit not in durations:
        await ctx.send("Invalid duration! Use `1H`, `5H`, `12H`, or `24H`.")
        return

    hours = durations[unit]
    key_code = f"AETHERIUS-{uuid.uuid4().hex[:8].upper()}"
    expire_timestamp = (datetime.datetime.utcnow() + datetime.timedelta(hours=hours)).timestamp()

    keys = load_keys()
    keys[key_code] = {
        "expires_at": expire_timestamp,
        "claimed_user": None,
        "duration": unit
    }
    save_keys(keys)

    try:
        embed = discord.Embed(title="Aetherius X - Key Generated", color=0x00C3FF)
        embed.add_field(name="Key", value=f"`{key_code}`", inline=False)
        embed.add_field(name="Duration", value=unit, inline=True)
        embed.set_footer(text="Locks to the first Roblox account that redeems it.")
        await ctx.author.send(embed=embed)
        await ctx.send(f"✅ Key sent to your DMs, {ctx.author.mention}!")
    except discord.Forbidden:
        await ctx.send(f"❌ Could not DM you, {ctx.author.mention}. Enable DMs in Privacy Settings.")

async def handle_verify(request):
    key = request.query.get("key")
    user_id = request.query.get("user_id")

    if not key or not user_id:
        return web.json_response({"valid": False, "reason": "Missing key or user_id parameters"}, status=400)

    keys = load_keys()
    now = datetime.datetime.utcnow().timestamp()

    if key not in keys:
        return web.json_response({"valid": False, "reason": "Invalid Key"})

    key_info = keys[key]

    if now > key_info["expires_at"]:
        del keys[key]
        save_keys(keys)
        return web.json_response({"valid": False, "reason": "Key has expired"})

    if key_info["claimed_user"] is None:
        key_info["claimed_user"] = str(user_id)
        save_keys(keys)
    elif key_info["claimed_user"] != str(user_id):
        return web.json_response({"valid": False, "reason": "Key bound to another Roblox account"})

    return web.json_response({
        "valid": True,
        "expires_at": key_info["expires_at"],
        "claimed_user": key_info["claimed_user"]
    })

async def main():
    app = web.Application()
    app.router.add_get("/verify", handle_verify)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    print(f"[API] Server live on port {API_PORT}")
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

