import discord
from discord.ext import commands
import random
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.guild_messages = True

# Botのインスタンス作成
bot = commands.Bot(command_prefix="!", intents=intents)

# 環境変数からTOKENを取得
TOKEN = os.getenv('DISCORD_TOKEN')  # Herokuに環境変数として設定しておくべき

# フォーラムチャンネルとスレッドのID
FORUM_CHANNEL_ID = 1288321432828248124  # フォーラムのチャンネルID
THREAD_ID = 1288407362318893109  # 対象のスレッドID

@bot.event
async def on_ready():
    print(f"Bot is ready as {bot.user}")
    try:
        synced = await bot.tree.sync()  # コマンド同期
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# ランダムなおすすめのメッセージを送信するコマンド
@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    try:
        # ターゲットのフォーラムチャンネルとスレッドの取得
        forum_channel = bot.get_channel(FORUM_CHANNEL_ID)
        if forum_channel is None:
            await interaction.response.send_message(f"フォーラムチャンネルが見つかりませんでした（ID: {FORUM_CHANNEL_ID}）", ephemeral=True)
            return

        # スレッド取得
        thread = forum_channel.get_thread(THREAD_ID)
        if thread is None:
            await interaction.response.send_message(f"スレッドが見つかりませんでした（ID: {THREAD_ID}）", ephemeral=True)
            return

        # スレッドからメッセージを取得
        messages = [message async for message in thread.history(limit=100)]
        if not messages:
            await interaction.response.send_message("スレッド内にメッセージがありませんでした。", ephemeral=True)
            return

        # ランダムでメッセージを選択
        random_message = random.choice(messages)

        # ランダムメッセージを送信
        if random_message.content:
            await interaction.response.send_message(f"おすすめの漫画: {random_message.content}")
        else:
            await interaction.response.send_message("取得したメッセージが空でした。", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)
        print(f"Error occurred: {e}")

# Botの起動
if __name__ == "__main__":
    if TOKEN:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"Bot起動中にエラーが発生しました: {e}")
    else:
        print("DISCORD_TOKENが設定されていません。")
