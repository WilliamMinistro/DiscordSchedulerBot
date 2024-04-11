import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
from collections import defaultdict, Counter
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

class TimeSlotButton(Button):
    def __init__(self, time_slot, user_id, disabled=False):
        super().__init__(style=discord.ButtonStyle.primary, label=time_slot.split(' ')[-1], disabled=disabled)
        self.time_slot = time_slot
        self.user_id = user_id
        self.disabled = disabled

    async def callback(self, interaction: discord.Interaction):
        if not self.disabled:
            self.view.response_data[self.user_id].add(self.time_slot)
            selected_times = ', '.join(sorted(self.view.response_data[self.user_id]))
            await interaction.response.send_message(f"You've selected: {selected_times}.", ephemeral=True)

class ScheduleView(View):
    def __init__(self, date_range, user_id, title, description):
        super().__init__()
        self.title = title
        self.description = description
        self.response_data = defaultdict(set)

        start_date, end_date = [datetime.strptime(date, '%Y-%m-%d') for date in date_range.split(':')]
        while start_date <= end_date:
            date_str = start_date.strftime('%Y-%m-%d (%A)')
            self.add_item(Button(label=date_str, style=discord.ButtonStyle.secondary, disabled=True))
            for time_of_day in ["Morning", "Afternoon", "Evening"]:
                time_slot_str = f"{date_str} {time_of_day}"
                self.add_item(TimeSlotButton(time_slot=time_slot_str, user_id=user_id))
            start_date += timedelta(days=1)

@bot.slash_command(name="startschedulesurvey", description="Start a survey to schedule an event.")
async def start_schedule_survey(interaction: discord.Interaction, survey_duration: discord.Option(int, "Duration of the survey in minutes"),
                                date_range: discord.Option(str, "Date range for the survey formatted as YYYY-MM-DD:YYYY-MM-DD"),
                                title: discord.Option(str, "Title of the survey"),
                                description: discord.Option(str, "Description of the survey")):
    await interaction.response.defer(ephemeral=False)
    user_id = interaction.user.id
    view = ScheduleView(date_range, user_id, title, description)
    
    await interaction.followup.send(
        f"**{title}**\n{description}\n\nSelect as many dates and times as you'd like. The survey will run for {survey_duration} minutes.", 
        view=view
    )

    await asyncio.sleep(survey_duration * 60)

    counter = Counter()
    for user, times in view.response_data.items():
        counter.update(times)

    sorted_times = counter.most_common()
    best_time, best_count = sorted_times[0] if sorted_times else ("No times selected.", 0)
    second_best_time, second_best_count = (sorted_times[1] if len(sorted_times) > 1 else ("No second best time.", 0))

    can_attend_best = {user for user, times in view.response_data.items() if best_time in times}
    can_attend_second_best = {user for user, times in view.response_data.items() if second_best_time in times}

    cannot_attend_best = set(view.response_data.keys()) - can_attend_best
    cannot_attend_second_best = set(view.response_data.keys()) - can_attend_second_best

    can_attend_best_members = [await bot.fetch_user(user_id) for user_id in can_attend_best]
    can_attend_second_best_members = [await bot.fetch_user(user_id) for user_id in can_attend_second_best]

    cannot_attend_best_members = [await bot.fetch_user(user_id) for user_id in cannot_attend_best]
    cannot_attend_second_best_members = [await bot.fetch_user(user_id) for user_id in cannot_attend_second_best]

    can_attend_best_msg = ', '.join(member.mention for member in can_attend_best_members)
    can_attend_second_best_msg = ', '.join(member.mention for member in can_attend_second_best_members) or "None"

    cannot_attend_best_msg = ', '.join(member.mention for member in cannot_attend_best_members) or "None"
    cannot_attend_second_best_msg = ', '.join(member.mention for member in cannot_attend_second_best_members) or "None"

    result_message = (f"Survey completed.\n"
                      f"The best time slot is: {best_time} with {best_count} participants available.\n"
                      f"The second best time slot is: {second_best_time} with {second_best_count} participants available.\n\n"
                      f"Can attend the best time: {can_attend_best_msg}\n"
                      f"Can attend the second best time: {can_attend_second_best_msg}\n"
                      f"Cannot attend the best time: {cannot_attend_best_msg}\n"
                      f"Cannot attend the second best time: {cannot_attend_second_best_msg}")

    try:
        await interaction.followup.send(result_message)
    except discord.HTTPException as e:
        print(f"Failed to send survey results: {e}")

bot.run(os.getenv("DISCORD_BOT_KEY"))