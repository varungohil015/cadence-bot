import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

import database as db
from utils import utcnow, utcnow_str, get_week_start, progress_bar


# In-memory store for active sessions
# {user_id: {"start": datetime, "duration": int, "message": discord.Message, "task": str, "channel_id": int}}
active_sessions: dict = {}


def build_session_embed(user: discord.User | discord.Member, elapsed: int, duration: int, task: str) -> discord.Embed:
    bar = progress_bar(elapsed, duration)
    remaining = duration - elapsed
    color = 0xFF6B35 if elapsed < duration else 0x57F287

    embed = discord.Embed(
        title="🍅 Pomodoro Session",
        color=color,
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    embed.add_field(name="Task", value=f"`{task}`", inline=False)
    embed.add_field(name="Progress", value=f"{bar}\n{elapsed} / {duration} min", inline=False)
    if elapsed < duration:
        embed.set_footer(text=f"{remaining} min remaining — stay locked in 💪")
    else:
        embed.set_footer(text="Session complete! Take a break 🎉")
    return embed


class TaskSelectView(discord.ui.View):
    def __init__(self, tasks: list, user_id: int, duration: int):
        super().__init__(timeout=60)
        self.chosen_task = None
        self.user_id = user_id
        self.duration = duration

        options = [discord.SelectOption(label=t["title"][:100], value=str(t["id"])) for t in tasks[:25]]
        options.append(discord.SelectOption(label="➕ New task...", value="__new__"))

        select = discord.ui.Select(placeholder="Choose a task for this session...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your session.", ephemeral=True)
            return
        self.chosen_task = interaction.data["values"][0]
        self.stop()
        await interaction.response.defer()


class NewTaskModal(discord.ui.Modal, title="New Task"):
    task_name = discord.ui.TextInput(label="Task name", placeholder="What will you work on?", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.stop()


class Pomodoro(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _is_screen_sharing(self, member: discord.Member) -> bool:
        return (
            member.voice is not None
            and member.voice.channel is not None
            and (member.voice.self_stream or member.voice.self_video)
        )

    @app_commands.command(name="start", description="Start a Pomodoro session. Must be in VC and screen sharing.")
    @app_commands.describe(duration="Session length in minutes (default 25)")
    async def start(self, interaction: discord.Interaction, duration: int = 25):
        if not await db.is_user_joined(interaction.user.id):
            await interaction.response.send_message("Use `/join` first to start using Cadence.", ephemeral=True)
            return

        if interaction.user.id in active_sessions:
            await interaction.response.send_message("You already have an active session. Use `/stop` to end it.", ephemeral=True)
            return

        if not self._is_screen_sharing(interaction.user):
            await interaction.response.send_message(
                "You need to be in a voice channel **and** screen sharing (Go Live) to start a session.",
                ephemeral=True,
            )
            return

        if duration < 1 or duration > 120:
            await interaction.response.send_message("Duration must be between 1 and 120 minutes.", ephemeral=True)
            return

        # Fetch open tasks for select menu
        open_tasks = await db.get_open_tasks(interaction.user.id)
        task_label = "General Focus"

        if open_tasks:
            view = TaskSelectView([{"id": t["id"], "title": t["title"]} for t in open_tasks], interaction.user.id, duration)
            await interaction.response.send_message("Choose a task for this session:", view=view, ephemeral=True)
            await view.wait()

            if view.chosen_task is None:
                await interaction.edit_original_response(content="Session cancelled — no task selected.", view=None)
                return

            if view.chosen_task == "__new__":
                modal = NewTaskModal()
                # Can't send modal after already responded — create new task inline
                task_label = "New Task"
            else:
                row = next((t for t in open_tasks if str(t["id"]) == view.chosen_task), None)
                task_label = row["title"] if row else "General Focus"

            await interaction.edit_original_response(content="Session starting...", view=None)
        else:
            await interaction.response.defer()

        now = utcnow()
        active_sessions[interaction.user.id] = {
            "start": now,
            "duration": duration,
            "task": task_label,
            "channel_id": interaction.channel_id,
            "guild_id": interaction.guild_id,
        }

        embed = build_session_embed(interaction.user, 0, duration, task_label)

        if open_tasks:
            msg = await interaction.followup.send(embed=embed, wait=True)
        else:
            msg = await interaction.followup.send(embed=embed, wait=True)

        active_sessions[interaction.user.id]["message_id"] = msg.id
        active_sessions[interaction.user.id]["channel_id"] = msg.channel.id

        # Start background tick
        self.bot.loop.create_task(self._tick(interaction.user, duration))

    async def _tick(self, user: discord.User | discord.Member, duration: int):
        user_id = user.id
        for elapsed in range(1, duration + 1):
            await asyncio.sleep(60)

            session = active_sessions.get(user_id)
            if session is None:
                return  # Session was stopped early

            channel = self.bot.get_channel(session["channel_id"])
            if channel is None:
                continue

            try:
                msg = await channel.fetch_message(session["message_id"])
            except discord.NotFound:
                return

            embed = build_session_embed(user, elapsed, duration, session["task"])
            await msg.edit(embed=embed)

            if elapsed >= duration:
                # Auto-complete
                await self._complete_session(user_id, user, completed=True)
                return

    async def _complete_session(self, user_id: int, user: discord.User | discord.Member, completed: bool):
        session = active_sessions.pop(user_id, None)
        if session is None:
            return

        now = utcnow()
        start: datetime = session["start"]
        elapsed_min = int((now - start).total_seconds() / 60)
        is_complete = completed and elapsed_min >= int(session["duration"] * 0.8)

        await db.log_pomodoro(
            user_id, session["guild_id"],
            start.isoformat(), now.isoformat(),
            session["duration"], is_complete,
        )

        if is_complete:
            await db.update_weekly_score(user_id, session["guild_id"], get_week_start(), pomodoros=1)

        # DM the user
        try:
            dm = await user.create_dm()
            if is_complete:
                await dm.send(f"🔔 Pomodoro complete! Great work on `{session['task']}`. Take a break.")
            else:
                await dm.send(f"⏹️ Session stopped early (`{session['task']}`). No points this time.")
        except discord.Forbidden:
            pass

    @app_commands.command(name="stop", description="Stop your current Pomodoro session.")
    async def stop(self, interaction: discord.Interaction):
        if interaction.user.id not in active_sessions:
            await interaction.response.send_message("You don't have an active session.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self._complete_session(interaction.user.id, interaction.user, completed=False)
        await interaction.followup.send("Session stopped.", ephemeral=True)

    @app_commands.command(name="status", description="Check your current Pomodoro session progress.")
    async def status(self, interaction: discord.Interaction):
        session = active_sessions.get(interaction.user.id)
        if session is None:
            await interaction.response.send_message("No active session. Use `/start` to begin.", ephemeral=True)
            return

        now = utcnow()
        elapsed = int((now - session["start"]).total_seconds() / 60)
        embed = build_session_embed(interaction.user, elapsed, session["duration"], session["task"])
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Pomodoro(bot))
