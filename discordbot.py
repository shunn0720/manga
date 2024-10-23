@bot.tree.command(name="おすすめ漫画", description="おすすめの漫画をランダムで表示します")
async def recommend_manga(interaction: discord.Interaction):
    # すぐに仮応答を返す（応答保留）
    await interaction.response.defer(ephemeral=True)

    # スレッドIDを指定してメッセージ履歴を取得
    thread_id = 1288407362318893109  # スレッドIDをここで指定
    thread = bot.get_channel(thread_id)

    if thread is None:
        await interaction.followup.send("指定されたスレッドが見つかりませんでした。スレッドIDを確認してください。", ephemeral=True)
        return

    # メッセージ履歴を非同期で収集
    messages = []
    async for message in thread.history(limit=100):
        if message.author.id != interaction.user.id:  # メッセージを送信したユーザーがコマンドの実行者と異なることを確認
            messages.append(message)

    if not messages:
        await interaction.followup.send("他のユーザーのメッセージが見つかりませんでした。", ephemeral=True)
        return
    
    random_message = random.choice(messages)

    # ランダムメッセージのリンクを生成
    random_message_url = f"https://discord.com/channels/{random_message.guild.id}/{random_message.channel.id}/{random_message.id}"

    random_thread_user = random_message.author

    mention = f"<@{interaction.user.id}>"
    response_message = (f"{mention} さんには、「{random_thread_user.name}」さんが投稿したこの本がおすすめだよ！\n"
                        f"{random_message_url}")

    # その後にメッセージを送信
    target_channel = bot.get_channel(1297537770574581841)
    await target_channel.send(response_message)

    # フォローアップメッセージとして応答を送信
    await interaction.followup.send("おすすめを表示しました！", ephemeral=True)
