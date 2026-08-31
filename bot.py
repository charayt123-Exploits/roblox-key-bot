import os
import json
import asyncio
from aiohttp import web
import discord
from discord.ext import commands

# ---------------------------------------------------------
# SETUP & CONFIGURATION
# ---------------------------------------------------------
# Reads token from environment variable set in Render dashboard
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Setup Discord bot client with basic intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Temporary local key storage (JSON fallback)
KEYS_FILE = "keys.json"

def load_keys():
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=4)

keys_db = load_keys()

# ---------------------------------------------------------
# DISCORD BOT EVENTS & COMMANDS
# ---------------------------------------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("Discord Bot is online and ready!")

@bot.command(name="generatekey")
@commands.has_permissions(administrator=True)
async def generate_key(ctx, key_name: str):
    """Generates a key for Roblox authentication."""
    keys_db[key_name] = {"valid": True, "created_by": str(ctx.author)}
    save_keys(keys_db)
    await ctx.send(f"Key `{key_name}` generated successfully!")

# ---------------------------------------------------------
# AIOHTTP WEB SERVER (ROBLOX KEY API)
# ---------------------------------------------------------
async def handle_root(request):
    """Health check route for Render."""
    return web.Response(text="Aetherius Key System API is running online!")

async def handle_verify_key(request):
    """API endpoint for Roblox script to verify keys."""
    key = request.query.get("key", None)
    
    if not key:
        return web.json_response({"success": False, "message": "No key provided"}, status=400)
    
    if key in keys_db and keys_db[key].get("valid", False):
        return web.json_response({"success": True, "message": "Key is valid!"})
    else:
        return web.json_response({"success": False, "message": "Invalid or expired key"}, status=403)

async def start_web_server():
    """Starts the web server on the PORT provided by Render environment."""
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/verify", handle_verify_key)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render assigns dynamic port numbers via os.getenv("PORT")
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web API server running on port {port}")

# ---------------------------------------------------------
# MAIN ASYNC RUNNER
# ---------------------------------------------------------
async def main():
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN environment variable not set.")
        return

    # Run both the web server and the Discord bot on the same event loop
    await start_web_server()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

