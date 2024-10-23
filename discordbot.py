@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    # すぐに応答を保留（defer）
    await interaction.response.defer(ephemeral=True)

    # メッセージ履歴の取得
    fetch_channel_id = 1297538136225878109
    fetch_channel = bot.get_channel(fetch_channel_id)

    # メッセージ履歴を非同期で収集する
    messages = []
    async for message in fetch_channel.history(limit=100):
        messages.append(message)

    if not messages:
        await interaction.followup.send("メッセージが見つかりませんでした。")
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
        await interaction.followup.send("他のユーザーがいないため、おすすめできません。")
        return
    
    random_thread_user = random.choice(thread_messages).author

    mention = f"<@{interaction.user.id}>"
    response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                        f"{random_message_url}")

    # その後にメッセージを送信
    target_channel = bot.get_channel(1297537770574581841)
    await target_channel.send(response_message)

    # フォローアップメッセージとして応答を送信
    await interaction.followup.send("おすすめを表示しました！")
