# discordbot.py
# -*- coding: utf-8 -*-
"""
MCP＋DB 完全対応 おみくじ Bot 2025-05-25
────────────────────────────────────────
● GPT-4o（MCP）でツッコミ／罵倒／結果コメント
● PostgreSQL で回数・履歴・週替り無限引き管理
● 毎日 1 % 抽選で当日限定無限引き
● 2 回目・3 回目以降は GPT 関西弁罵倒
● /omikuji_all でギルド全員の履歴一括リセット（管理者のみ）
● Embed パネルを再表示するとき、**過去のパネルを history() で探して削除**（通知は出ない）
"""
# flake8: noqa: E501

from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timedelta, time, timezone
from typing import Set

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from openai import AsyncOpenAI

# ────────── 基本設定 ──────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not (TOKEN and DATABASE_URL and OPENAI_KEY):
    logging.error("環境変数が不足しています。")
    raise SystemExit(1)

openai_client = AsyncOpenAI(api_key=OPENAI_KEY)

JST = timezone(timedelta(hours=9))

# ────────── サーバー／管理者 ──────────
GUILD_ID = 1304798975513071658  # SlashCmd を登録するギルド
ADMIN_IDS = {822460191118721034, 802807293070278676}

# 週替り無限抽選候補チャンネル
WEEKLY_SRC_CHANNELS = [1304813185920139306, 1304813222058004522]

# ────────── おみくじ定義 ──────────
NUM_EMOJI_MAP = {i: f"{i}⃣" if i <= 10 else f"1⃣{i-10}⃣" for i in range(1, 16)}
DIRECTIONS = ["東", "西", "南", "北"]
LUCKY_COLORS = [
    "白", "黒", "シルバー", "グレイ", "赤", "栗色", "黄色", "オリーブ色", "ライム", "緑",
    "アクア", "ティール", "青", "ネイビー", "フクシャ", "紫",
]

FORTUNES = [
    ("鯖の女神降臨", 0.1, [
        "推しとエロイプ待ったなし！？",
        "感度MAX!!イキまくり間違えなし！？",
        "相性最高の人と出会える！？",
        "自分から誘えば百戦錬磨？！",
    ]),
    ("大吉", 2.0, [
        "気になるあの子をエロイプに誘ったらいいんちゃうん！？知らんけど",
        "新しいおもちゃ買ったらめっちゃ気持ちいんちゃうん！？知らんけど",
        "今あの子もあんたとイプしたいんちゃうん！？知らんけど",
        "今日リップ音の調子めっちゃいいんちゃうん！？知らんけど",
        "会議あがったらめっちゃモテるんちゃうん！？知らんけど",
    ]),
    ("中吉", 10, [
        "えっちな画像が見れるかも！？",
        "いつもより感度がいいかも！？",
        "新たな癖の開発が出来るかも！？",
        "欲しいおもちゃがセール中かも？？",
        "自撮りエチ画爆盛れかも！？",
    ]),
    ("小吉", 20, [
        "おっぱいで窒息死♡",
        "ちんちんで圧迫死♡ｵｪｵｪ",
        "愛に包まれ尊し♡",
        "逆転で今日はやり返し♡",
        "今日は貴方が一番星♡",
    ]),
    ("吉", 30, [
        "イケメン、美女の食べ過ぎ注意",
        "Beyourloverの部屋間違え注意",
        "タラ置き去り注意",
        "フラグに界隈バレ注意",
        "喘ぎ声音量注意",
    ]),
    ("凶", 25, [
        "パンツをのぞこうとして石につまづくかも？",
        "おかず探しに時間を使いすぎて萎えちゃうかも？",
        "玩具の充電切れてるかも？？",
        "大好きなあの人が今日はフラグかも？",
        "今日は心のちんちんの勃ちが悪いかも？",
    ]),
    ("大凶", 12.8, [
        "voice投稿せんかったらもう今日1日あんた不幸まみれやで？ｗｗ",
        "おっぱい!!いっぱい!!大しっぱい!!うぇえい!!",
        "うちに秘めた癖を会議で暴露せなその癖一生理解されへんで！？ｗｗ",
        "最近いつエロイプしたか暴露しないと次のエロイプは半年後になるで！？ｗｗ",
        "MBTIにとらわれたら誰ともえっちなこと出来ひんくなるかもしれへんで？ｗｗ",
    ]),
    ("救いようがない日", 0.1, [
        "公開せえへんかったら今後エロイプは出来ひんようになるで？",
        "18禁に画像を上げましょう。さすれば貴方は救われる････といいね😇",
        "会議で18禁失敗談を何か一つ暴露せえへんと大きなイベントに参加出来なくなるんちゃう？",
        "ソロオナ公開せなオナニーでイケへんようになるで？",
    ]),
]

# ────────── 時間ユーティリティ ──────────
def jst_now() -> datetime:
    return datetime.now(JST)


def today() -> datetime.date:
    return jst_now().date()


def yesterday() -> datetime.date:
    return today() - timedelta(days=1)


def two_days_ago() -> datetime.date:
    return today() - timedelta(days=2)


# ────────── GPT ラッパー ──────────
async def gpt(uid: int, sys: str, user: str) -> str:
    try:
        rsp = await openai_client.chat.completions.create(
            model="gpt-4o",
            user=str(uid),
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            max_tokens=60,
            temperature=0.9,
        )
        return rsp.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"GPT Error: {e}")
        return "……（AIが黙っとる）"


# ────────── おみくじ抽選 ──────────
def choose_fortune() -> tuple[str, str]:
    total = sum(w for _, w, _ in FORTUNES)
    pick = random.uniform(0, total)
    cum = 0
    for name, weight, msgs in FORTUNES:
        cum += weight
        if pick <= cum:
            return name, random.choice(msgs)
    name, _, msgs = FORTUNES[-1]
    return name, random.choice(msgs)


# ────────── Discord Bot ──────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# DB & 状態
db_pool: asyncpg.Pool | None = None
lucky_today_users: Set[int] = set()


# ────────── View ──────────
class OmikujiView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="おみくじを引く", style=discord.ButtonStyle.primary, custom_id="persistent_omikuji_button")
    async def draw(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)

        uid = interaction.user.id
        today_date = today()

        # ================= DBフェッチ =================
        async with db_pool.acquire() as conn:
            today_cnt_row = await conn.fetchrow(
                "SELECT count FROM omikuji_history WHERE user_id=$1 AND date=$2", uid, today_date
            )
            y_row = await conn.fetchrow(
                "SELECT result FROM omikuji_results WHERE user_id=$1 AND date=$2", uid, yesterday()
            )
            two_row = await conn.fetchrow(
                "SELECT result FROM omikuji_results WHERE user_id=$1 AND date=$2", uid, two_days_ago()
            )

            # 週替り無限
            monday = today_date - timedelta(days=today_date.weekday())
            weekly = await conn.fetchval(
                "SELECT 1 FROM omikuji_unlimited_users WHERE user_id=$1 AND week_start=$2", uid, monday
            )
            unlimited = bool(weekly) or uid in lucky_today_users

            # ===== 2回目 / 3回目罵倒 =====
            if today_cnt_row and today_cnt_row["count"] >= 2 and not unlimited:
                prompt_lv = "3回目以上" if today_cnt_row["count"] >= 2 else "2回目"
                tsukkomi = await gpt(
                    uid,
                    "あなたは関西弁で煽るおみくじBotです。",
                    f"ユーザーが今日{prompt_lv}のおみくじを引こうとしている。短い罵倒コメントを1文。",
                )
                await conn.execute(
                    "UPDATE omikuji_history SET count = count + 1 WHERE user_id=$1 AND date=$2", uid, today_date
                )
                await interaction.followup.send(f"{interaction.user.mention} {tsukkomi}")
                return

            # ===== 回数インクリメント =====
            await conn.execute(
                """
                INSERT INTO omikuji_history (user_id, date, count)
                VALUES ($1, $2, 1)
                ON CONFLICT (user_id,date) DO UPDATE SET count = omikuji_history.count + 1
                """,
                uid,
                today_date,
            )

        # ===== 1% 当日 lucky =====
        if not unlimited and random.random() <= 0.01:
            lucky_today_users.add(uid)
            unlimited = True
            await interaction.followup.send(embed=discord.Embed(title="今日はラッキー！無限に引けるで！", color=0xFFFF00))

        # ===== 抽選前 GPT コメント =====
        two_res = two_row["result"] if two_row else "なし"
        y_res = y_row["result"] if y_row else "なし"
        pre_msg = await gpt(
            uid,
            "あなたは関西弁で軽妙にツッコむおみくじBotです。",
            f"ユーザーの過去2日間の運勢は『{two_res}』『{y_res}』です。\n"
            "1行目: ツッコミ、2行目: 今おみくじ選んでる演出 → 2文で返してください。",
        )
        await interaction.followup.send(pre_msg)

        # ===== おみくじ結果 =====
        r_name, r_msg = choose_fortune()
        direction = random.choice(DIRECTIONS)
        num = random.randint(1, 15)
        color = random.choice(LUCKY_COLORS)

        embed = discord.Embed(
            title="おみくじ",
            description=(
                f"{interaction.user.mention} さんの本日の運勢は！\n\n"
                f"【運勢】\n{r_name}\n{r_msg}\n\n"
                f"【ラッキーな方角】\n{direction}\n\n"
                f"【ラッキーナンバー】\n{NUM_EMOJI_MAP[num]}\n\n"
                f"【ラッキーカラー】\n{color}"
            ),
            color=0x1E90FF,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.followup.send(embed=embed)

        # ===== 結果コメント GPT =====
        after_msg = await gpt(
            uid,
            "あなたは関西弁で相手をイジるおみくじBotです。",
            f"ユーザーが『{r_name}』を引きました。1文の短いコメントを返してください。",
        )
        await interaction.followup.send(after_msg)

        # ===== 結果保存 =====
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO omikuji_results (user_id,date,result,message)
                VALUES ($1,$2,$3,$4)
                ON CONFLICT (user_id,date) DO UPDATE
                SET result=$3, message=$4
                """,
                uid,
                today_date,
                r_name,
                r_msg,
            )

        # ===== 旧パネル Embed 削除処理（history 走査） =====
        try:
            async for m in interaction.channel.history(limit=50):
                if m.author == bot.user and m.embeds:
                    if "今日の運勢" in (m.embeds[0].title or ""):
                        await m.delete()
                        break
        except Exception:
            pass

        # ===== 新パネル再送信 =====
        panel_embed = discord.Embed(
            title="<:531:1320411500812439633>今日の運勢<:531:1320411500812439633>",
            description="ボタンを押しておみくじを引いてね<:041:1359536607559946470>",
            color=0x00FF00,
        )
        await interaction.channel.send(embed=panel_embed, view=OmikujiView())


# ────────── Slash Commands ──────────
CMD_KWARGS = dict(guild=discord.Object(id=GUILD_ID), default_member_permissions=discord.Permissions(0))


@tree.command(name="omikuji", description="おみくじパネルを出す", **CMD_KWARGS)
async def cmd_omikuji(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません。", ephemeral=True)
        return
    panel = discord.Embed(
        title="<:531:1320411500812439633>今日の運勢<:531:1320411500812439633>",
        description="ボタンを押しておみくじを引いてね<:041:1359536607559946470>",
        color=0x00FF00,
    )
    await interaction.response.send_message(embed=panel, view=OmikujiView())


@tree.command(name="omikuji_reset", description="指定ユーザーの履歴をリセット", **CMD_KWARGS)
@app_commands.describe(user="対象ユーザー")
async def cmd_reset(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません。", ephemeral=True)
        return
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM omikuji_history WHERE user_id=$1", user.id)
        await conn.execute("DELETE FROM omikuji_results WHERE user_id=$1", user.id)
    await interaction.response.send_message(f"{user.mention} の履歴を消しました。")


@tree.command(name="omikuji_all", description="サーバー全員の履歴をリセット", **CMD_KWARGS)
async def cmd_all(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("権限がありません。", ephemeral=True)
        return
    await interaction.response.defer(thinking=True, ephemeral=True)
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE omikuji_history")
        await conn.execute("TRUNCATE omikuji_results")
    await interaction.followup.edit_message(interaction.response.id, content="全員の履歴をリセットしました。")


# ────────── BG Tasks ──────────
@tasks.loop(time=time(0, 0, 0, tzinfo=JST))
async def clear_daily_lucky():
    lucky_today_users.clear()
    logging.info("当日 1% lucky セットをクリア")


@tasks.loop(time=time(0, 0, 0, tzinfo=JST))
async def weekly_pick():
    if today().weekday() != 0:  # 月曜のみ
        return
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    ids: Set[int] = set()
    after_dt = jst_now() - timedelta(days=7)
    for cid in WEEKLY_SRC_CHANNELS:
        ch = guild.get_channel(cid)
        if not isinstance(ch, discord.TextChannel):
            continue
        async for m in ch.history(limit=None, after=after_dt):
            if not m.author.bot:
                ids.add(m.author.id)
    choose = random.sample(list(ids), k=min(3, len(ids)))
    monday = today()
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM omikuji_unlimited_users WHERE week_start=$1", monday)
        for uid in choose:
            await conn.execute(
                "INSERT INTO omikuji_unlimited_users (user_id, week_start) VALUES ($1,$2)", uid, monday
            )
    logging.info(f"週替り無限引きユーザー更新: {choose}")


# ────────── 起動時処理 ──────────
@bot.event
async def on_ready():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS omikuji_history (
                user_id BIGINT NOT NULL,
                date DATE NOT NULL,
                count INT DEFAULT 0,
                PRIMARY KEY (user_id,date)
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS omikuji_results (
                user_id BIGINT NOT NULL,
                date DATE NOT NULL,
                result TEXT,
                message TEXT,
                PRIMARY KEY (user_id,date)
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS omikuji_unlimited_users (
                user_id BIGINT PRIMARY KEY,
                week_start DATE NOT NULL
            );
            """
        )
    bot.add_view(OmikujiView())
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    clear_daily_lucky.start()
    weekly_pick.start()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


if __name__ == "__main__":
    bot.run(TOKEN)
