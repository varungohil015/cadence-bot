import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone

import database as db
from utils import utcnow_str


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="join", description="Opt into Cadence — start tracking your productivity.")
    async def join(self, interaction: discord.Interaction):
        if await db.is_user_joined(interaction.user.id):
            await interaction.response.send_message("You're already in Cadence.", ephemeral=True)
            return

        await db.add_user(interaction.user.id, interaction.guild_id, utcnow_str())
        embed = discord.Embed(
            title="Welcome to Cadence 🎯",
            description=(
                "You're in. Here's what you can do:\n\n"
                "`/start` — Pomodoro session (VC + screen share required)\n"
                "`/add-task` — Add a task\n"
                "`/water` — Toggle water reminders\n"
                "`/stats` — Your weekly stats"
            ),
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leave", description="Opt out of Cadence.")
    async def leave(self, interaction: discord.Interaction):
        if not await db.is_user_joined(interaction.user.id):
            await interaction.response.send_message("You're not in Cadence.", ephemeral=True)
            return

        await db.remove_user(interaction.user.id)
        await interaction.response.send_message("You've left Cadence. Your data has been removed.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
