import discord
from discord import app_commands
from discord.ext import commands

import database as db
from utils import get_week_start


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="stats", description="View your personal weekly stats.")
    async def stats(self, interaction: discord.Interaction):
        if not await db.is_user_joined(interaction.user.id):
            await interaction.response.send_message("Use `/join` first.", ephemeral=True)
            return

        week = get_week_start()
        row = await db.get_weekly_stats(interaction.user.id, week)

        pomodoros = row["pomodoros"] if row else 0
        tasks_done = row["tasks_done"] if row else 0
        water_logs = row["water_logs"] if row else 0
        score = row["score"] if row else 0

        embed = discord.Embed(
            title=f"📊 Weekly Stats",
            color=0x5865F2,
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        embed.add_field(name="🍅 Pomodoros", value=str(pomodoros), inline=True)
        embed.add_field(name="✅ Tasks Done", value=str(tasks_done), inline=True)
        embed.add_field(name="💧 Water Logs", value=str(water_logs), inline=True)
        embed.add_field(
            name="Score Formula",
            value=f"`({pomodoros} × 50) + ({tasks_done} × 20) + ({water_logs} × 10) = **{score} pts**`",
            inline=False,
        )
        embed.set_footer(text="Resets every Monday 00:00 UTC")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="View the weekly team leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction):
        week = get_week_start()
        rows = await db.get_leaderboard(interaction.guild_id, week)

        if not rows:
            await interaction.response.send_message("No scores this week yet. Start a session!", ephemeral=True)
            return

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows):
            prefix = medals[i] if i < 3 else f"`#{i+1}`"
            try:
                user = await interaction.guild.fetch_member(row["user_id"])
                name = user.display_name
            except Exception:
                name = f"User {row['user_id']}"
            lines.append(f"{prefix} **{name}** — {row['score']} pts  _(🍅 {row['pomodoros']} · ✅ {row['tasks_done']} · 💧 {row['water_logs']})_")

        embed = discord.Embed(
            title="🏆 Weekly Leaderboard",
            description="\n".join(lines),
            color=0xFFD700,
        )
        embed.set_footer(text="Resets every Monday 00:00 UTC")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))
