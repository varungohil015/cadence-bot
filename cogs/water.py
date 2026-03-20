import asyncio
import discord
from discord import app_commands
from discord.ext import commands

import database as db
from utils import utcnow_str, get_week_start


# In-memory tracking of active reminder loops
# {user_id: asyncio.Task}
reminder_tasks: dict[int, asyncio.Task] = {}


class DrankView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Drank ✅", style=discord.ButtonStyle.success, custom_id="water_drank")
    async def drank(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your reminder.", ephemeral=True)
            return
        await db.log_hydration(interaction.user.id, utcnow_str())
        # Find guild_id for scoring — best effort from mutual guilds
        for guild in interaction.client.guilds:
            if guild.get_member(interaction.user.id):
                await db.update_weekly_score(
                    interaction.user.id, guild.id, get_week_start(), water_logs=1
                )
                break
        await interaction.response.edit_message(content="💧 Logged! **+10 pts** Keep it up.", view=None)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, custom_id="water_skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your reminder.", ephemeral=True)
            return
        await interaction.response.edit_message(content="Skipped. Remember to hydrate soon! 💧", view=None)


async def _reminder_loop(bot: commands.Bot, user_id: int, interval: int):
    """Sends a DM water reminder every `interval` minutes."""
    while True:
        await asyncio.sleep(interval * 60)

        reminder = await db.get_water_reminder(user_id)
        if reminder is None or not reminder["active"]:
            reminder_tasks.pop(user_id, None)
            return

        try:
            user = await bot.fetch_user(user_id)
            dm = await user.create_dm()
            await dm.send(
                "💧 **Cadence Hydration Check** — time to drink some water!",
                view=DrankView(user_id),
            )
        except (discord.Forbidden, discord.NotFound):
            pass


class Water(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Re-register reminder loops for users who had active reminders before restart
        async with __import__("aiosqlite").connect("cadence.db") as db_conn:
            async with db_conn.execute("SELECT user_id, interval FROM water_reminders WHERE active = 1") as cur:
                rows = await cur.fetchall()
        for row in rows:
            user_id, interval = row[0], row[1]
            if user_id not in reminder_tasks:
                task = self.bot.loop.create_task(_reminder_loop(self.bot, user_id, interval))
                reminder_tasks[user_id] = task

    @app_commands.command(name="water", description="Toggle water reminders on or off.")
    @app_commands.describe(interval="Reminder interval in minutes (default 30). Use 0 to turn off.")
    async def water(self, interaction: discord.Interaction, interval: int = 30):
        if not await db.is_user_joined(interaction.user.id):
            await interaction.response.send_message("Use `/join` first.", ephemeral=True)
            return

        user_id = interaction.user.id
        existing = await db.get_water_reminder(user_id)

        # Toggle off if already active with same interval, or if interval = 0
        if interval == 0 or (existing and existing["active"] and interval == existing["interval"]):
            await db.set_water_reminder(user_id, existing["interval"] if existing else 30, active=False)
            task = reminder_tasks.pop(user_id, None)
            if task:
                task.cancel()
            await interaction.response.send_message("💧 Water reminders turned **off**.", ephemeral=True)
            return

        # Turn on / update interval
        await db.set_water_reminder(user_id, interval, active=True)

        # Cancel old loop if running
        old_task = reminder_tasks.pop(user_id, None)
        if old_task:
            old_task.cancel()

        task = self.bot.loop.create_task(_reminder_loop(self.bot, user_id, interval))
        reminder_tasks[user_id] = task

        await interaction.response.send_message(
            f"💧 Water reminders **on** — I'll DM you every **{interval} min**.\n"
            "Run `/water 0` or `/water` again to turn off.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Water(bot))
