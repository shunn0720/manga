import discord
import random
import os
from discord import app_commands
from discord.ext import commands

# 必要なIntentsを有効化
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True  # ギルド関連のインテントも有効にする
bot = commands.Bot(command_prefix="!", intents=intents)

# 特定のギルドIDでスラッシュコマンドを同期するための変数
GUILD_ID = 123456789012345678  # ここにあなたのテストギルドのIDを入力してください

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    try:
        # 特定のギルドにスラッシュコマンドを同期
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands to guild {GUILD_ID}.")
        for command in bot.tree.get_commands():
            print(f"Registered command: {command.name}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# 簡単なpingコマンドで動作確認
@bot.tree.command(name="ping", description="チェック用のスラッシュコマンド")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# おすすめ漫画コマンド
@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    fetch_channel_id = 1297538136225878109  # 書き込みを取得するチャンネルID
    fetch_channel = bot.get_channel(fetch_channel_id)
    
    # チャンネルからメッセージ履歴を取得
    messages = await fetch_channel.history(limit=100).flatten()
    random_message = random.choice(messages)
    
    # ランダムメッセージのリンクを生成
    random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"
    
    # スレッドの情報を取得してランダムにユーザーを選ぶ
    thread_id = 1288407362318893109  # スレッドID
    thread = bot.get_channel(thread_id)
    thread_messages = await thread.history(limit=100).flatten()
    
    # 実行者以外のメッセージを取得
    eligible_messages = [msg for msg in thread_messages if msg.author.id != interaction.user.id]
    
    if not eligible_messages:
        await interaction.response.send_message("他のユーザーがいないため、おすすめできません。", ephemeral=True)
        return
    
    random_thread_user = random.choice(eligible_messages).author
    
    # 実行者にメンションを作成
    mention = f"<@{interaction.user.id}>"
    
    # 実行者の名前、ランダムに選ばれたユーザー、メッセージリンクをフォーマット
    response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                        f"{random_message_url}")
    
    # 応答をエフェメラルメッセージ（本人にだけ表示）として送信
    await interaction.response.send_message("おすすめを表示しました！", ephemeral=True)

    # 実際のメッセージはターゲットチャンネルに送信する
    target_channel = bot.get_channel(1297537770574581841)  # ターゲットチャンネルID
    await target_channel.send(response_message)

# ボット所有者用の手動コマンド同期コマンド
@bot.command()
@commands.is_owner()
async def sync(ctx):
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await ctx.send(f"Synced {len(synced)} commands to guild {GUILD_ID}.")
    except Exception as e:
        await ctx.send(f"Failed to sync commands: {e}")

# Herokuの環境変数からDiscordトークンを取得してボットを起動
try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except discord.errors.LoginFailure as e:
    print(f"Login failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
