import discord
import random
import os
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
    try:
        # チャンネルとスレッドID
        forum_channel_id = 1288321432828248124  # フォーラムチャンネルID
        thread_id = 1288407362318893109  # スレッドID
        target_channel_id = 1297537770574581841  # メッセージを表示するチャンネルID

        # ターゲットチャンネルの取得
        target_channel = bot.get_channel(target_channel_id)
        if target_channel is None:
            await interaction.response.send_message(f"ターゲットチャンネルが見つかりませんでした（ID: {target_channel_id}）。", ephemeral=True)
            return

        # フォーラムスレッドの取得
        thread = bot.get_channel(thread_id)
        if thread is None:
            await interaction.response.send_message(f"スレッドが見つかりませんでした（ID: {thread_id}）。", ephemeral=True)
            return

        # スレッド内のメッセージ履歴の取得
        thread_messages = [message async for message in thread.history(limit=100)]
        eligible_messages = [msg for msg in thread_messages if msg.author.id != interaction.user.id]

        if not eligible_messages:
            await interaction.response.send_message("他のユーザーがいないため、おすすめできません。", ephemeral=True)
            return

        # ランダムにメッセージを選択
        random_thread_user = random.choice(eligible_messages).author
        mention = f"<@{interaction.user.id}>"
        random_message_url = f"https://discord.com/channels/{thread.guild.id}/{thread.id}/{eligible_messages[0].id}"

        response_message = (
            f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
            f"{random_message_url}"
        )

        # ターゲットチャンネルにメッセージを送信
        await target_channel.send(response_message)
        await interaction.response.send_message("おすすめを表示しました！", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

@bot.command()
@commands.is_owner()
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands.")
    except Exception as e:
        await ctx.send(f"Failed to sync commands: {e}")

# ボットを起動
bot.run(os.getenv('DISCORD_TOKEN'))
