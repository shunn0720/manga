import discord
import random
import os
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
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# おすすめ漫画コマンド
@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    # すぐに仮応答を返す（応答保留）
    await interaction.response.defer(ephemeral=True)

    # メッセージ履歴の取得
    fetch_channel_id = 1297538136225878109
    fetch_channel = bot.get_channel(fetch_channel_id)

    # メッセージ履歴を非同期で収集する
    messages = []
    async for message in fetch_channel.history(limit=100):
        messages.append(message)

    if not messages:
        await interaction.followup.send("メッセージが見つかりませんでした。", ephemeral=True)
        return
    
    random_message = random.choice(messages)

    # ランダムメッセージのリンクを生成
    random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"

    # スレッドの情報を取得してランダムにユーザーを選ぶ
    thread_id = 1288407362318893109
    thread = bot.get_channel(thread_id)

    thread_messages = []
    async for thread_message in thread.history(limit=100):
        if thread_message.author.id != interaction.user.id:
            thread_messages.append(thread_message)

    if not thread_messages:
        await interaction.followup.send("他のユーザーがいないため、おすすめできません。", ephemeral=True)
        return
    
    random_thread_user = random.choice(thread_messages).author

    mention = f"<@{interaction.user.id}>"
    response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                        f"{random_message_url}")

    # その後にメッセージを送信
    target_channel = bot.get_channel(1297537770574581841)
    await target_channel.send(response_message)

    # フォローアップメッセージとして応答を送信
    await interaction.followup.send("おすすめを表示しました！", ephemeral=True)

# Herokuの環境変数からDiscordトークンを取得してボットを起動
try:
    bot.run(os.getenv('DISCORD_TOKEN'))
except discord.errors.LoginFailure as e:
    print(f"Login failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
