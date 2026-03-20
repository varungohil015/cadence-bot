import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

import database

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

COGS = [
    "cogs.general",
    "cogs.pomodoro",
    "cogs.tasks",
    "cogs.water",
    "cogs.stats",
]


class Cadence(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await database.init_db()

        for cog in COGS:
            await self.load_extension(cog)
            print(f"  Loaded {cog}")

        # Sync slash commands to the guild for instant availability
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"  Synced {len(synced)} slash commands to guild {GUILD_ID}")

    async def on_ready(self):
        print(f"\nCadence online — logged in as {self.user} ({self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="you stay productive 🍅",
            )
        )


async def main():
    async with Cadence() as bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
