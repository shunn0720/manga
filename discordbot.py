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
        for command in bot.tree.get_commands():
            print(f"Registered command: {command.name}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    # メッセージを取得するチャンネルID
    fetch_channel_id = 1297538136225878109
    fetch_channel = bot.get_channel(fetch_channel_id)
    
    if fetch_channel is None:
        await interaction.response.send_message(f"メッセージ取得用のチャンネルが見つかりませんでした（ID: {fetch_channel_id}）", ephemeral=True)
        return

    # メッセージ履歴を取得
    try:
        messages = [msg async for msg in fetch_channel.history(limit=100)]
        if not messages:
            await interaction.response.send_message("メッセージが見つかりませんでした。", ephemeral=True)
            return
    except Exception as e:
        await interaction.response.send_message(f"メッセージ履歴の取得に失敗しました: {str(e)}", ephemeral=True)
        return

    random_message = random.choice(messages)
    random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"
    
    # スレッド内のメッセージを取得する
    thread_id = 1288407362318893109
    thread = bot.get_channel(thread_id)
    
    if thread is None:
        await interaction.response.send_message(f"スレッドが見つかりませんでした（ID: {thread_id}）", ephemeral=True)
        return

    # スレッドメッセージを取得
    try:
        thread_messages = [msg async for msg in thread.history(limit=100)]
        if not thread_messages:
            await interaction.response.send_message("スレッド内のメッセージが見つかりませんでした。", ephemeral=True)
            return
    except Exception as e:
        await interaction.response.send_message(f"スレッドメッセージの取得に失敗しました: {str(e)}", ephemeral=True)
        return

    # 自分以外のユーザーからのメッセージをフィルタリング
    eligible_messages = [msg for msg in thread_messages if msg.author.id != interaction.user.id]
    if not eligible_messages:
        await interaction.response.send_message("他のユーザーがいないため、おすすめできません。", ephemeral=True)
        return

    random_thread_user = random.choice(eligible_messages).author
    mention = f"<@{interaction.user.id}>"
    
    # レスポンスメッセージ作成
    response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                        f"{random_message_url}")
    
    # メッセージを送信するチャンネルにメッセージを送信
    target_channel_id = 1297538136225878109
    target_channel = bot.get_channel(target_channel_id)
    
    if target_channel is None:
        await interaction.response.send_message(f"ターゲットチャンネルが見つかりませんでした（ID: {target_channel_id}）", ephemeral=True)
        return
    
    try:
        await target_channel.send(response_message)
    except Exception as e:
        await interaction.response.send_message(f"メッセージ送信に失敗しました: {str(e)}", ephemeral=True)
        return

    await interaction.response.send_message("おすすめメッセージを送信しました！", ephemeral=True)

@bot.command()
@commands.is_owner()
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands.")
    except Exception as e:
        await ctx.send(f"Failed to sync commands: {e}")

# Botの実行
try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except discord.errors.LoginFailure as e:
    print(f"Login failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
