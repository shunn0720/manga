import discord
import random
import os
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    fetch_channel_id = 1297538136225878109
    fetch_channel = bot.get_channel(fetch_channel_id)
    messages = await fetch_channel.history(limit=100).flatten()
    random_message = random.choice(messages)
    random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"
    thread_id = 1288407362318893109
    thread = bot.get_channel(thread_id)
    thread_messages = await thread.history(limit=100).flatten()
    eligible_messages = [msg for msg in thread_messages if msg.author.id != interaction.user.id]
    if not eligible_messages:
        await interaction.response.send_message("他のユーザーがいないため、おすすめできません。", ephemeral=True)
        return
    random_thread_user = random.choice(eligible_messages).author
    mention = f"<@{interaction.user.id}>"
    response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                        f"{random_message_url}")
    await interaction.response.send_message("おすすめを表示しました！", ephemeral=True)
    target_channel = bot.get_channel(1297537770574581841)
    await target_channel.send(response_message)

try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except Exception as e:
    print(f"Error occurred: {e}")
