import discord
import random
import os  # 環境変数を取得するためのモジュール
from discord.ext import commands
from discord.ui import Button, View

intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容を取得するためのIntent
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')

# ボタンが押されたときに発生するアクション
class RecommendButton(Button):
    def __init__(self, fetch_channel_id, target_channel_id, thread_id):
        super().__init__(label="おすすめを取得", style=discord.ButtonStyle.primary)
        self.fetch_channel_id = fetch_channel_id
        self.target_channel_id = target_channel_id
        self.thread_id = thread_id  # スレッドIDを保持

    async def callback(self, interaction: discord.Interaction):
        # メッセージを取得するチャンネルを指定
        fetch_channel = bot.get_channel(self.fetch_channel_id)
        messages = await fetch_channel.history(limit=100).flatten()  # メッセージ履歴を取得

        # ランダムにメッセージを1つ選び、メッセージリンクを取得
        random_message = random.choice(messages)
        random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"

        # スレッドの情報を取得してランダムにユーザーを選ぶ（ただし、ボタンを押したユーザーを除外）
        thread = bot.get_channel(self.thread_id)  # スレッドを取得
        thread_messages = await thread.history(limit=100).flatten()  # スレッド内のメッセージ履歴を取得

        # ボタンを押したユーザーを除外したメッセージのリストを作成
        eligible_messages = [msg for msg in thread_messages if msg.author.id != interaction.user.id]

        # 重複しないユーザーが存在するかチェック
        if not eligible_messages:
            await interaction.response.send_message("他のユーザーがいないため、おすすめできません。", ephemeral=True)
            return

        # ボタンを押したユーザーと被らないランダムなユーザーを取得
        random_thread_user = random.choice(eligible_messages).author

        # 投稿先チャンネルを取得
        target_channel = bot.get_channel(self.target_channel_id)

        # 押したユーザーのIDを使ってメンションを作成
        mention = f"<@{interaction.user.id}>"

        # 押したユーザーの名前と、スレッドからランダムに選ばれたユーザー、メッセージリンクをフォーマット
        response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                            f"{random_message_url}")

        # 指定したチャンネルにメッセージを送信
        await target_channel.send(response_message)

        # ボタンを押したユーザーに一時的な応答を送る（インタラクション失敗防止）
        await interaction.response.send_message("おすすめが送信されました！", ephemeral=True)

# ボタンを設置するための関数
def recommend_button(channel_id, fetch_channel_id, target_channel_id, thread_id):
    button = RecommendButton(fetch_channel_id=fetch_channel_id, 
                             target_channel_id=target_channel_id, 
                             thread_id=thread_id)  # ボタンのインスタンス作成
    view = View()
    view.add_item(button)
    
    # チャンネルにボタン付きメッセージを送信
    channel = bot.get_channel(channel_id)
    return channel.send("おすすめを確認したい方は、ボタンを押してください！", view=view)

# コマンドを使って簡単にボタンを設置
@bot.command()
async def setup(ctx):
    # ボタンを特定のチャンネルに設置
    await recommend_button(channel_id=1297538136225878109, 
                           fetch_channel_id=1297538136225878109, 
                           target_channel_id=1297537770574581841, 
                           thread_id=1288407362318893109)

# Herokuの環境変数からトークンを取得
bot.run(os.getenv('DISCORD_TOKEN'))
