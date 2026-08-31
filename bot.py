import os
import time
import secrets
import asyncio
from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_CHANNEL_ID = 1521535812343169124

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

keys_db = {}

def clean_expired_keys():
    now = time.time()
    expired = [k for k, v in keys_db.items() if now > v["expires_at"]]
    for k in expired:
        del keys_db[k]

def user_has_active_key(discord_user_id):
    clean_expired_keys()
    for v in keys_db.values():
        if v["creator_id"] == discord_user_id:
            return True
    return False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="generatekey", description="Generate your unique Roblox access key.")
@app_commands.choices(duration=[
    app_commands.Choice(name="1 Hour", value=1),
    app_commands.Choice(name="5 Hours", value=5),
    app_commands.Choice(name="12 Hours", value=12),
    app_commands.Choice(name="24 Hours", value=24),
])
async def generate_key(interaction: discord.Interaction, duration: app_commands.Choice[int]):
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Commands can only be used in <#{ALLOWED_CHANNEL_ID}>!", 
            ephemeral=True
        )
        return

    if user_has_active_key(interaction.user.id):
        await interaction.response.send_message(
            "❌ You already have an active key! Wait until it expires.", 
            ephemeral=True
        )
        return

    hours_selected = duration.value
    duration_seconds = hours_selected * 3600
    expires_at = time.time() + duration_seconds
    generated_key = f"KEY-{secrets.token_hex(4).upper()}"

    keys_db[generated_key] = {
        "creator_id": interaction.user.id,
        "expires_at": expires_at,
        "duration_hours": hours_selected,
        "roblox_user_id": None
    }

    await interaction.response.send_message(
        f"✅ Key **`{generated_key}`** generated successfully!\n"
        f"⏱️ **Expires in:** {hours_selected} Hour(s)\n"
        f"🔒 **Status:** Unlocked (Locks to first Roblox Account that redeems it).",
        ephemeral=True
    )

async def handle_root(request):
    return web.Response(text="Aetherius Key System API is running online!")

async def handle_verify_key(request):
    clean_expired_keys()
    key = request.query.get("key", None)
    roblox_id = request.query.get("roblox_id", None)
    
    if not key or not roblox_id:
        return web.json_response({"success": False, "message": "Missing parameters"}, status=400)
    
    try:
        roblox_id = int(roblox_id)
    except ValueError:
        return web.json_response({"success": False, "message": "Invalid Roblox ID"}, status=400)

    if key not in keys_db:
        return web.json_response({"success": False, "message": "Invalid or expired key"}, status=403)
    
    key_data = keys_db[key]
    
    if key_data["roblox_user_id"] is None:
        key_data["roblox_user_id"] = roblox_id
    elif key_data["roblox_user_id"] != roblox_id:
        return web.json_response({"success": False, "message": "Key bound to another Roblox account!"}, status=403)

    return web.json_response({"success": True, "message": "Key valid!"})

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/verify", handle_verify_key)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web API server running on port {port}")

async def main():
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN missing")
        return
    await start_web_server()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
