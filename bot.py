import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime, timedelta
import pytz  # Import pytz for timezone support

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True  # Required for voice state detection
intents.members = True
bot = commands.Bot(command_prefix='>>', intents=intents)

# Remove the default help command
bot.remove_command('help')

# Helper function to send messages as embeds
async def send_embed(ctx, title, description, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)

# Dictionary to track alarms
alarms = {}
# Dictionary to store AFK statuses
afk_users = {}

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user}')

@bot.command()
async def alarm(ctx, time: str = None):
    """
    Sets an alarm at the given time (24-hour format: HH:MM) in Indian Standard Time (IST).
    If the user is in a voice channel, the bot will play an alarm sound for 30 seconds.
    Otherwise, it will tag the user.
    """
    if time is None:
        await send_embed(ctx, "Error", "You need to provide a time for the alarm. Usage: `>>alarm HH:MM`", discord.Color.red())
        return

    # Parse the time
    try:
        hours, minutes = map(int, time.split(":"))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError
    except ValueError:
        await send_embed(ctx, "Error", "Invalid time format! Please use HH:MM (24-hour format).", discord.Color.red())
        return

    # Set the time zone to India Standard Time (IST)
    india_tz = pytz.timezone("Asia/Kolkata")

    # Get the current time in IST
    now = datetime.now(india_tz)
    alarm_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)

    # If the alarm time is in the past, set it for the next day
    if alarm_time < now:
        alarm_time += timedelta(days=1)

    # Calculate the time difference in seconds
    delay = (alarm_time - now).total_seconds()

    await send_embed(ctx, "Alarm Set", f"Alarm set for {time} IST! I'll remind you.", discord.Color.green())

    # Wait until the alarm time
    await asyncio.sleep(delay)

    # Check if the user is in a voice channel
    if ctx.author.voice:
        voice_channel = ctx.author.voice.channel
        try:
            # Attempt to connect to the voice channel
            vc = await voice_channel.connect()
            await send_embed(ctx, "Joined Voice Channel", f"Joined voice channel: {voice_channel.name}", discord.Color.blue())

            # Play the alarm sound
            audio_source = discord.FFmpegPCMAudio("alarm.mp3")
            vc.play(audio_source, after=lambda e: print(f"Finished playing: {e}"))

            # Wait for 30 seconds or until the sound finishes
            await asyncio.sleep(30)

            # Disconnect after playing the alarm
            if vc.is_playing():
                vc.stop()
            await vc.disconnect()
            await send_embed(ctx, "Alarm Finished", "Alarm finished, leaving the voice channel.", discord.Color.blue())
        except Exception as e:
            await send_embed(ctx, "Error", f"Failed to join voice channel: {e}", discord.Color.red())
            print(f"Error while joining voice channel: {e}")
    else:
        await send_embed(ctx, "No Voice Channel", f"{ctx.author.mention}, you're not in a voice channel! 🔔", discord.Color.red())

@bot.command()
async def afk(ctx, *, reason="I'm busy right now."):  # Default reason
    afk_users[ctx.author.id] = reason
    await send_embed(ctx, "AFK Set", f"{ctx.author.mention} is now AFK: {reason}", discord.Color.green())

@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author.bot:
        return

    # If the user is AFK and sends a message, remove their AFK status
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(embed=discord.Embed(
            title="Welcome Back",
            description=f"Welcome back, {message.author.mention}! I removed your AFK status.",
            color=discord.Color.blue()
        ))

    # Check if a mentioned user is AFK
    mentioned_afk_users = [
        mention for mention in message.mentions if mention.id in afk_users
    ]
    for mention in mentioned_afk_users:
        reason = afk_users[mention.id]
        await message.channel.send(embed=discord.Embed(
            title="AFK Alert",
            description=f"{mention.mention} is currently AFK: {reason}",
            color=discord.Color.orange()
        ))

    # Process other commands
    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await send_embed(ctx, "Pong!", f'Pong! {latency}ms', discord.Color.blue())

@bot.command()
async def help(ctx):
    """
    Sends an embed with a list of available commands and their descriptions.
    """
    help_text = (
        "**>>alarm [time]** - Set an alarm at the given time (24-hour format HH:MM). The bot will either join your voice channel and play a sound or tag you if not in a voice channel.\n"
        "**>>afk [reason]** - Set your status to AFK with an optional reason.\n"
        "**>>ping** - Checks the bot's latency.\n"
        "**>>help** - Displays this help message with information about the bot's commands.\n"
    )

    await send_embed(ctx, "Help - Available Commands", help_text, discord.Color.blue())

# Start the bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN not found in .env file")