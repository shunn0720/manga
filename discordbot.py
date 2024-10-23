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
        # フォーラムのチャンネルIDとスレッドIDを指定
        forum_channel_id = 1288321432828248124  # フォーラムチャンネルのID
        thread_id = 1288407362318893109  # スレッドID
        
        # フォーラムチャンネルにアクセス（必要であれば確認）
        forum_channel = bot.get_channel(forum_channel_id)
        if forum_channel is None:
            await interaction.followup.send(f"フォーラムチャンネル {forum_channel_id} にアクセスできませんでした。", ephemeral=True)
            return
        
        # スレッドにアクセスしてメッセージ履歴を取得
        thread = bot.get_channel(thread_id)
        if thread is None:
            await interaction.followup.send(f"スレッドID {thread_id} にアクセスできませんでした。", ephemeral=True)
            return

        # メッセージ履歴を非同期で取得（最新100件）
        messages = []
        async for message in thread.history(limit=100):
            if message.author.id != interaction.user.id:  # 実行者以外のメッセージを取得
                messages.append(message)

        if not messages:
            await interaction.followup.send("他のユーザーのメッセージが見つかりませんでした。", ephemeral=True)
            return

        # ランダムにメッセージを選択
        random_message = random.choice(messages)
        random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"
        random_thread_user = random_message.author

        # 応答メッセージを構成
        mention = f"<@{interaction.user.id}>"
        response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                            f"{random_message_url}")

        # ターゲットチャンネルを取得
        target_channel_id = 1297537770574581841  # 投稿先のチャンネルID
        target_channel = bot.get_channel(target_channel_id)

        if target_channel is None:
            await interaction.followup.send(f"ターゲットチャンネルが見つかりませんでした（ID: {target_channel_id}）。", ephemeral=True)
            return

        # ターゲットチャンネルに送信
        await target_channel.send(response_message)

        # 最終的な応答をフォローアップで返す
        await interaction.followup.send("おすすめを表示しました！", ephemeral=True)

    except Exception as e:
        # エラーハンドリング
        await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)
        print(f"Error: {e}")

# デバッグ用：ボットがアクセスできるチャンネル一覧を確認するコマンド
@bot.tree.command(name="デバッグチャンネル", description="ボットが認識しているチャンネルを確認します")
async def debug_channels(interaction: discord.Interaction):
    guild = interaction.guild
    channels = guild.channels
    channel_list = "\n".join([f"{channel.name} (ID: {channel.id})" for channel in channels])

    # 取得したチャンネル一覧を送信
    await interaction.response.send_message(f"ボットが認識しているチャンネル一覧:\n{channel_list}", ephemeral=True)

# Herokuの環境変数からDiscordトークンを取得してボットを起動
try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except discord.errors.LoginFailure as e:
    print(f"Login failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
