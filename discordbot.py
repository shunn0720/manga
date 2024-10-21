import discord
import random
import os  # 環境変数を取得するためのモジュール
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容を取得するためのIntent
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# スラッシュコマンド /おすすめ漫画 の実装
@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    # メッセージを取得するチャンネルを指定（以前の fetch_channel_id）
    fetch_channel_id = 1297538136225878109
    fetch_channel = bot.get_channel(fetch_channel_id)
    messages = await fetch_channel.history(limit=100).flatten()  # メッセージ履歴を取得

    # ランダムにメッセージを1つ選び、メッセージリンクを取得
    random_message = random.choice(messages)
    random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"

    # スレッドの情報を取得してランダムにユーザーを選ぶ（以前の thread_id）
    thread_id = 1288407362318893109
    thread = bot.get_channel(thread_id)  # スレッドを取得
    thread_messages = await thread.history(limit=100).flatten()  # スレッド内のメッセージ履歴を取得

    # コマンドを実行したユーザーを除外したメッセージのリストを作成
    eligible_messages = [msg for msg in thread_messages if msg.author.id != interaction.user.id]

    # 重複しないユーザーが存在するかチェック
    if not eligible_messages:
        await interaction.response.send_message("他のユーザーがいないため、おすすめできません。", ephemeral=True)
        return

    # 実行したユーザーと被らないランダムなユーザーを取得
    random_thread_user = random.choice(eligible_messages).author

    # コマンドを実行したユーザーにメンションを作成
    mention = f"<@{interaction.user.id}>"

    # 実行したユーザーの名前と、スレッドからランダムに選ばれたユーザー、メッセージリンクをフォーマット
    response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                        f"{random_message_url}")

    # 応答をエフェメラルメッセージとして送信（誰にも見えない）
    await interaction.response.send_message("おすすめを表示しました！", ephemeral=True)

    # 実際のメッセージはターゲットチャンネルに送信する
    target_channel = bot.get_channel(1297537770574581841)
    await target_channel.send(response_message)

# Herokuの環境変数からトークンを取得
bot.run(os.getenv('DISCORD_TOKEN'))
