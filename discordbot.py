import discord
import random
import os
from discord import app_commands
from discord.ext import commands

# Intentsを設定
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

# おすすめ漫画のスラッシュコマンド
@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    # 応答を保留し、仮応答を返す
    await interaction.response.defer(ephemeral=True)

    try:
        # スレッドIDを指定してメッセージ履歴を取得
        thread_id = 1288407362318893109  # スレッドIDは指定済み
        thread = bot.get_channel(thread_id)

        if thread is None:
            await interaction.followup.send("指定されたスレッドが見つかりませんでした。", ephemeral=True)
            return

        # メッセージ履歴を非同期で取得
        messages = []
        async for message in thread.history(limit=100):
            if message.author.id != interaction.user.id:  # 実行者以外のメッセージを取得
                messages.append(message)

        if not messages:
            await interaction.followup.send("他のユーザーのメッセージが見つかりませんでした。", ephemeral=True)
            return

        random_message = random.choice(messages)

        # ランダムメッセージのリンクを生成
        random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"
        random_thread_user = random_message.author

        # 応答メッセージを構成
        mention = f"<@{interaction.user.id}>"
        response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                            f"{random_message_url}")

        # ターゲットチャンネルに送信
        target_channel = bot.get_channel(1297537770574581841)
        await target_channel.send(response_message)

        # 最終的な応答をフォローアップで返す
        await interaction.followup.send("おすすめを表示しました！", ephemeral=True)

    except Exception as e:
        # エラーハンドリング
        await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)
        print(f"Error: {e}")

# Herokuの環境変数からDiscordトークンを取得してボットを起動
try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except discord.errors.LoginFailure as e:
    print(f"Login failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
