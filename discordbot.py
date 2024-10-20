import discord
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
    def __init__(self, fetch_channel_id):
        super().__init__(label="おすすめを取得", style=discord.ButtonStyle.primary)
        self.fetch_channel_id = fetch_channel_id

    async def callback(self, interaction: discord.Interaction):
        # メッセージを取得するチャンネルを指定
        fetch_channel = bot.get_channel(self.fetch_channel_id)
        messages = await fetch_channel.history(limit=100).flatten()  # メッセージ履歴を取得

        # ランダムにメッセージを1つ選ぶ
        random_message = random.choice(messages)
        full_message_content = random_message.content

        # 「【タイトル】」行の後の部分を抽出
        title_line = None
        for line in full_message_content.splitlines():
            if "【タイトル】" in line:
                title_line = line.replace("【タイトル】", "").strip()  # 「【タイトル】」を除いた部分を取得
                break

        # 押したユーザーの名前と、ランダムに選ばれたメッセージからフォーマット
        if title_line:
            response_message = f"@{interaction.user.name} さんには、「{random_message.author.name}」さんが投稿した「{title_line}」がおすすめ！"
        else:
            response_message = f"@{interaction.user.name} さんには、「{random_message.author.name}」さんの投稿がおすすめですが、タイトルが見つかりませんでした。"

        # メッセージを送信
        await interaction.response.send_message(response_message, ephemeral=True)

# コマンドを使ってボタンを含むメッセージを送信
@bot.command()
async def recommend(ctx):
    # チャンネルIDに基づいて、抜き出すチャンネルとボタンの作成
    button = RecommendButton(fetch_channel_id=1297537770574581841)  # 抜き出し元チャンネルID
    view = View()
    view.add_item(button)

    # ボタンを設置するチャンネルにメッセージを送信
    target_channel = bot.get_channel(1297538136225878109)  # ボタンを設置するチャンネルID
    await target_channel.send("おすすめを確認したい方は、ボタンを押してください！", view=view)

bot.run('YOUR_BOT_TOKEN')
