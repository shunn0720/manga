import discord
import random
import os
from discord import app_commands
from discord.ext import commands

# ボットの初期化
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ボットが準備完了したときのイベント
@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# おすすめの漫画を表示するコマンド
@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    try:
        # フォーラムのチャンネルIDとスレッドID
        forum_channel_id = 1288321432828248124  # フォーラムチャンネルID
        thread_id = 1288407362318893109  # スレッドID
        fetch_channel_id = 1297538136225878109  # メッセージIDを取得するチャンネルID
        target_channel_id = 1297537770574581841  # おすすめメッセージを送るチャンネルID

        # ターゲットチャンネルの取得
        target_channel = bot.get_channel(target_channel_id)
        if target_channel is None:
            await interaction.response.send_message(f"ターゲットチャンネルが見つかりませんでした（ID: {target_channel_id}）。", ephemeral=True)
            return

        # メッセージを取得するチャンネルの取得
        fetch_channel = bot.get_channel(fetch_channel_id)
        if fetch_channel is None:
            await interaction.response.send_message(f"メッセージを取得するチャンネルが見つかりませんでした（ID: {fetch_channel_id}）。", ephemeral=True)
            return

        # チャンネルからメッセージ履歴を取得
        messages = [message async for message in fetch_channel.history(limit=100)]
        if not messages:
            await interaction.response.send_message("メッセージが見つかりませんでした。", ephemeral=True)
            return

        # ランダムにメッセージを選択
        random_message = random.choice(messages)
        random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"

        # スレッドの取得
        thread = bot.get_channel(thread_id)
        if thread is None:
            await interaction.response.send_message(f"スレッドが見つかりませんでした（ID: {thread_id}）。", ephemeral=True)
            return

        # スレッド内のメッセージ履歴を取得
        thread_messages = [message async for message in thread.history(limit=100)]
        eligible_messages = [msg for msg in thread_messages if msg.author.id != interaction.user.id]

        # 他のユーザーのメッセージがない場合
        if not eligible_messages:
            await interaction.response.send_message("他のユーザーがいないため、おすすめできません。", ephemeral=True)
            return

        # ランダムに他のユーザーのメッセージを選択
        random_thread_user = random.choice(eligible_messages).author
        mention = f"<@{interaction.user.id}>"
        response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                            f"{random_message_url}")

        # ターゲットチャンネルにメッセージを送信
        await target_channel.send(response_message)
        await interaction.response.send_message("おすすめを表示しました！", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

# ボットを起動する
try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except discord.errors.LoginFailure as e:
    print(f"Login failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
