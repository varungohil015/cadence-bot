import discord
from discord import app_commands
from discord.ext import commands

import database as db
from utils import utcnow_str, get_week_start


class Tasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add-task", description="Add a task to your list.")
    @app_commands.describe(title="What do you need to do?")
    async def add_task(self, interaction: discord.Interaction, title: str):
        if not await db.is_user_joined(interaction.user.id):
            await interaction.response.send_message("Use `/join` first.", ephemeral=True)
            return

        task_id = await db.add_task(interaction.user.id, interaction.guild_id, title, utcnow_str())
        await interaction.response.send_message(
            f"📝 Task added — `#{task_id}: {title}`", ephemeral=True
        )

    @app_commands.command(name="list-task", description="View your open tasks.")
    async def list_task(self, interaction: discord.Interaction):
        if not await db.is_user_joined(interaction.user.id):
            await interaction.response.send_message("Use `/join` first.", ephemeral=True)
            return

        tasks = await db.get_open_tasks(interaction.user.id)
        if not tasks:
            await interaction.response.send_message("No open tasks. Add one with `/add-task`.", ephemeral=True)
            return

        lines = [f"`#{t['id']}` {t['title']}" for t in tasks]
        embed = discord.Embed(
            title="Your Open Tasks",
            description="\n".join(lines),
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="done-task", description="Mark a task as complete.")
    @app_commands.describe(task_id="The task ID from /list-task")
    async def done_task(self, interaction: discord.Interaction, task_id: int):
        if not await db.is_user_joined(interaction.user.id):
            await interaction.response.send_message("Use `/join` first.", ephemeral=True)
            return

        success = await db.complete_task(task_id, interaction.user.id, utcnow_str())
        if not success:
            await interaction.response.send_message(
                f"Task `#{task_id}` not found or already completed.", ephemeral=True
            )
            return

        await db.update_weekly_score(
            interaction.user.id, interaction.guild_id, get_week_start(), tasks_done=1
        )
        await interaction.response.send_message(
            f"✅ Task `#{task_id}` marked complete! **+20 pts**", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Tasks(bot))
