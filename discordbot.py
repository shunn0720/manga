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

# おすすめのメッセージを表示するコマンド
@bot.tree.command(name="おすすめ漫画", description="フォーラムスレッドからランダムでメッセージを取得し表示します")
async def recommend_manga(interaction: discord.Interaction):
    try:
        # フォーラムのチャンネルIDとスレッドID
        forum_channel_id = 1288321432828248124  # フォーラムチャンネルID
        thread_id = 1288407362318893109  # メッセージを取得するスレッドID
        target_channel_id = 1297538136225878109  # メッセージ送信先のターゲットチャンネルID

        # ターゲットチャンネルの取得
        target_channel = bot.get_channel(target_channel_id)
        if target_channel is None:
            await interaction.response.send_message(f"ターゲットチャンネルが見つかりませんでした（ID: {target_channel_id}）。", ephemeral=True)
            return

        # フォーラムチャンネルからスレッドの取得
        forum_channel = bot.get_channel(forum_channel_id)
        if forum_channel is None:
            await interaction.response.send_message(f"フォーラムチャンネルが見つかりませんでした（ID: {forum_channel_id}）。", ephemeral=True)
            return

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
        random_message = random.choice(eligible_messages)

        mention = f"<@{interaction.user.id}>"
        random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"

        response_message = (f"{mention} さんには、「{random_message.author.name}」さんが投稿したこちらのメッセージがおすすめです！\n"
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
