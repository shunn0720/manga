import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import os
import random
import logging
import asyncio
from psycopg2 import pool, Error
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
import json


########################
# .env 環境変数読みこみ
########################
load_dotenv()


########################
# ログレベルの設定
########################
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "t")
log_level = logging.DEBUG if DEBUG_MODE else logging.INFO

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


########################
# 環境変数・定数
########################
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

THREAD_ID = os.getenv("THREAD_ID")
if THREAD_ID is None:
    logger.error("THREAD_IDが設定されていません。環境変数を確認してください。")
    exit(1)

try:
    THREAD_ID = int(THREAD_ID)
except ValueError:
    logger.error("THREAD_IDが無効な値です。正しいチャンネルID(数値)を設定してください。")
    exit(1)


########################
# リアクションIDの定義
########################
REACTIONS = {
    "b431": 1289782471197458495,  # <:b431:1289782471197458495> (ランダム除外)
    "b434": 1304690617405669376,  # <:b434:1304690617405669376> (あとで読む)
    "b435": 1304690627723657267   # <:b435:1304690627723657267> (お気に入り)
}

READ_LATER_REACTION_ID = REACTIONS["b434"]
FAVORITE_REACTION_ID = REACTIONS["b435"]
RANDOM_EXCLUDE_ID = REACTIONS["b431"]
SPECIFIC_EXCLUDE_USER = 695096014482440244


########################
# DB接続プール
########################
try:
    db_pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DATABASE_URL,
        sslmode="require"
    )
    logger.info("Database connection pool initialized.")
except Error as e:
    logger.error(f"Database connection pool initialization error: {e}")
    db_pool = None


def get_db_connection():
    if db_pool:
        try:
            return db_pool.getconn()
        except Error as e:
            logger.error(f"Error getting database connection: {e}")
            return None
    else:
        logger.error("Database connection pool is not initialized.")
        return None


def release_db_connection(conn):
    if db_pool and conn:
        try:
            db_pool.putconn(conn)
        except Error as e:
            logger.error(f"Error releasing database connection: {e}")


def initialize_db():
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                message_id BIGINT NOT NULL UNIQUE,
                thread_id BIGINT NOT NULL,
                author_id BIGINT NOT NULL,
                reactions JSONB DEFAULT '{}',
                content TEXT
            )
            """)
            conn.commit()
        logger.info("Database initialized successfully.")
    except Error as e:
        logger.error(f"Error initializing tables: {e}")
    finally:
        release_db_connection(conn)


initialize_db()


########################
# Botインテンツの設定
########################
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


########################
# ヘルパー変数・関数
########################
last_chosen_authors = {}


async def safe_fetch_message(channel, message_id):
    try:
        return await channel.fetch_message(message_id)
    except (discord.NotFound, discord.HTTPException):
        return None


async def ensure_message_in_db(message):
    if not message:
        return
    try:
        await asyncio.to_thread(_ensure_message_in_db_sync, message)
    except Exception as e:
        logger.error(f"Error ensuring message in DB: {e}")


def _ensure_message_in_db_sync(message):
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT id FROM messages WHERE message_id = %s", (message.id,))
            row = cur.fetchone()
            if row:
                return
            cur.execute("""
                INSERT INTO messages (message_id, thread_id, author_id, content)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (message.id, message.channel.id, message.author.id, message.content))
            conn.commit()
            logger.info(f"Inserted new message into DB (message_id={message.id}).")
    except Error as e:
        logger.error(f"Error ensuring message in DB: {e}")
    finally:
        release_db_connection(conn)


async def update_reactions_in_db(message_id, emoji_id, user_id, add=True):
    try:
        await asyncio.to_thread(_update_reactions_in_db_sync, message_id, emoji_id, user_id, add)
    except Exception as e:
        logger.error(f"Error updating reactions in DB: {e}")


def _update_reactions_in_db_sync(message_id, emoji_id, user_id, add=True):
    conn = get_db_connection()
    if not conn:
        return
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT reactions FROM messages WHERE message_id = %s", (message_id,))
            row = cur.fetchone()
            if not row:
                logger.info(f"No row found for message_id={message_id}, skip reaction update.")
                return
            reactions = row["reactions"] or {}
            if isinstance(reactions, str):
                try:
                    reactions = json.loads(reactions)
                except json.JSONDecodeError:
                    reactions = {}

            str_emoji_id = str(emoji_id)
            user_list = reactions.get(str_emoji_id, [])

            if add:
                if user_id not in user_list:
                    user_list.append(user_id)
            else:
                if user_id in user_list:
                    user_list.remove(user_id)

            reactions[str_emoji_id] = user_list
            new_json = json.dumps(reactions)
            cur.execute("""
                UPDATE messages
                SET reactions = %s
                WHERE message_id = %s
            """, (new_json, message_id))
            conn.commit()
            logger.info(f"Reactions updated for message_id={message_id}.")
    except Error as e:
        logger.error(f"Error updating reactions in DB: {e}")
    finally:
        release_db_connection(conn)


def user_reacted(msg, reaction_id, user_id):
    reaction_data = msg.get("reactions", {})
    if isinstance(reaction_data, str):
        try:
            reaction_data = json.loads(reaction_data)
        except json.JSONDecodeError:
            reaction_data = {}
    return user_id in reaction_data.get(str(reaction_id), [])


def _fetch_reactions_sync(msg_id):
    """
    対象メッセージのリアクションをDBから同期的に取得するヘルパー関数。
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT reactions FROM messages WHERE message_id = %s", (msg_id,))
            row = cur.fetchone()
            if not row:
                return None

            r = row["reactions"] or {}
            if isinstance(r, str):
                try:
                    r = json.loads(r)
                except json.JSONDecodeError:
                    r = {}
            return r
    except Error as e:
        logger.error(f"Error fetching reactions for message_id={msg_id}: {e}")
        return None
    finally:
        release_db_connection(conn)


async def get_random_message(thread_id, filter_func=None, button_name="N/A"):
    try:
        return await asyncio.to_thread(_get_random_message_sync, thread_id, filter_func, button_name)
    except Exception as e:
        logger.error(f"Error getting random message: {e}")
        return None


def _get_random_message_sync(thread_id, filter_func=None, button_name="N/A"):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM messages WHERE thread_id = %s", (thread_id,))
            rows = cur.fetchall()
            for m in rows:
                if m["reactions"] is None:
                    m["reactions"] = {}
                elif isinstance(m["reactions"], str):
                    try:
                        m["reactions"] = json.loads(m["reactions"]) or {}
                    except json.JSONDecodeError:
                        m["reactions"] = {}
            if filter_func:
                filtered = [row for row in rows if filter_func(row)]
                rows = filtered
            if not rows:
                return None
            return random.choice(rows)
    except Error as e:
        logger.error(f"Error fetching random message: {e}")
        return None
    finally:
        release_db_connection(conn)


########################
# Viewクラス
########################
class CombinedView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def get_author_name(self, author_id):
        user = bot.get_user(author_id)
        if user is None:
            try:
                user = await bot.fetch_user(author_id)
            except discord.NotFound:
                user = None
        if user:
            return user.display_name or user.name
        else:
            return f"UnknownUser({author_id})"

    async def handle_selection(self, interaction, random_message, user_id):
        if random_message:
            last_chosen_authors[user_id] = random_message["author_id"]
            author_name = await self.get_author_name(random_message["author_id"])
            await interaction.channel.send(
                f"{interaction.user.mention} さんには、{author_name} さんの投稿がおすすめだよ！\n"
                f"https://discord.com/channels/{interaction.guild_id}/{THREAD_ID}/{random_message['message_id']}"
            )
        else:
            await interaction.channel.send(
                f"{interaction.user.mention} さん、該当する投稿がありませんでした。"
            )
        await send_panel(interaction.channel)

    async def get_and_handle_random_message(self, interaction, filter_func, button_name="N/A"):
        await interaction.response.defer()
        random_msg = await get_random_message(THREAD_ID, filter_func=filter_func, button_name=button_name)
        await self.handle_selection(interaction, random_msg, interaction.user.id)

    @discord.ui.button(label="ランダム", style=discord.ButtonStyle.primary, row=0, custom_id="blue_random_unique_id")
    async def blue_random(self, interaction: discord.Interaction, button: discord.ui.Button):
        button_name = "blue_random"

        def filter_func(msg):
            if msg["author_id"] == interaction.user.id:
                return False
            if last_chosen_authors.get(interaction.user.id) == msg["author_id"]:
                return False
            if msg["author_id"] == SPECIFIC_EXCLUDE_USER:
                return False
            return True

        await self.get_and_handle_random_message(interaction, filter_func, button_name=button_name)

    @discord.ui.button(label="あとで読む", style=discord.ButtonStyle.primary, row=0, custom_id="read_later_unique_id")
    async def read_later(self, interaction: discord.Interaction, button: discord.ui.Button):
        button_name = "blue_read_later"

        def filter_func(msg):
            if not user_reacted(msg, READ_LATER_REACTION_ID, interaction.user.id):
                return False
            if msg["author_id"] == interaction.user.id:
                return False
            if last_chosen_authors.get(interaction.user.id) == msg["author_id"]:
                return False
            if msg["author_id"] == SPECIFIC_EXCLUDE_USER:
                return False
            return True

        await self.get_and_handle_random_message(interaction, filter_func, button_name=button_name)

    @discord.ui.button(label="お気に入り", style=discord.ButtonStyle.primary, row=0, custom_id="favorite_unique_id")
    async def favorite(self, interaction: discord.Interaction, button: discord.ui.Button):
        button_name = "blue_favorite"

        def filter_func(msg):
            if not user_reacted(msg, FAVORITE_REACTION_ID, interaction.user.id):
                return False
            if msg["author_id"] == interaction.user.id:
                return False
            if last_chosen_authors.get(interaction.user.id) == msg["author_id"]:
                return False
            if msg["author_id"] == SPECIFIC_EXCLUDE_USER:
                return False
            return True

        await self.get_and_handle_random_message(interaction, filter_func, button_name=button_name)

    @discord.ui.button(label="ランダム", style=discord.ButtonStyle.danger, row=1, custom_id="red_random_unique_id")
    async def red_random(self, interaction: discord.Interaction, button: discord.ui.Button):
        button_name = "red_random"

        def filter_func(msg):
            if user_reacted(msg, RANDOM_EXCLUDE_ID, interaction.user.id):
                return False
            if msg["author_id"] == interaction.user.id:
                return False
            if msg["author_id"] == SPECIFIC_EXCLUDE_USER:
                return False
            if last_chosen_authors.get(interaction.user.id) == msg["author_id"]:
                return False
            return True

        await self.get_and_handle_random_message(interaction, filter_func, button_name=button_name)

    @discord.ui.button(label="あとで読む", style=discord.ButtonStyle.danger, row=1, custom_id="conditional_read_later_unique_id")
    async def conditional_read_later(self, interaction: discord.Interaction, button: discord.ui.Button):
        button_name = "red_read_later"

        def filter_func(msg):
            if not user_reacted(msg, READ_LATER_REACTION_ID, interaction.user.id):
                return False
            if user_reacted(msg, RANDOM_EXCLUDE_ID, interaction.user.id):
                return False
            if msg["author_id"] == interaction.user.id:
                return False
            if last_chosen_authors.get(interaction.user.id) == msg["author_id"]:
                return False
            if msg["author_id"] == SPECIFIC_EXCLUDE_USER:
                return False
            return True

        await self.get_and_handle_random_message(interaction, filter_func, button_name=button_name)


########################
# 永続的なビューの登録
########################
@bot.event
async def on_ready():
    logger.info(f"Bot is online! {bot.user}")
    save_all_messages_to_db_task.start()
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        logger.error(f"Error syncing slash commands: {e}")
    bot.add_view(CombinedView())
    logger.info("Registered CombinedView as a persistent view.")


########################
# パネルの送信
########################
current_panel_message_id = None


async def send_panel(channel):
    global current_panel_message_id
    try:
        async for msg in channel.history(limit=100):
            if msg.author == bot.user and msg.embeds:
                embed = msg.embeds[0]
                if embed.title == "🎯 エロ漫画ルーレット":
                    await msg.delete()
                    logger.info(f"Deleted old panel message with ID {msg.id}.")
    except Exception as e:
        logger.error(f"Error deleting old panel messages: {e}")

    embed = create_panel_embed()
    view = CombinedView()
    try:
        sent_msg = await channel.send(embed=embed, view=view)
        current_panel_message_id = sent_msg.id
        logger.info(f"Sent new panel message with ID {current_panel_message_id}.")
    except discord.HTTPException as e:
        logger.error(f"Error sending panel message: {e}")


def create_panel_embed():
    embed = discord.Embed(
        title="🎯 エロ漫画ルーレット",
        description=(
            "ボタンを押してエロ漫画を選んでください！<a:c296:1288305823323263029>\n\n"
            "🔵：自分の <:b431:1289782471197458495> を除外しない\n"
            "🔴：自分の <:b431:1289782471197458495> を除外する\n\n"
            "**ランダム**：全体から選ぶ\n"
            "**あとで読む**：<:b434:1304690617405669376> を付けた投稿\n"
            "**お気に入り**：<:b435:1304690627723657267> を付けた投稿"
        ),
        color=0xFF69B4
    )
    return embed


########################
# スラッシュコマンド
########################
@bot.tree.command(name="embed", description="ルーレット用パネルを表示します。")
async def embed_command(interaction: discord.Interaction):
    channel = interaction.channel
    if channel:
        await interaction.response.send_message("パネルを表示します！", ephemeral=True)
        await send_panel(channel)
    else:
        await interaction.response.send_message("エラー: チャンネルが取得できませんでした。", ephemeral=True)


@bot.tree.command(name="check", description="特定のメッセージのリアクションを表示します。")
async def check_command(interaction: discord.Interaction, message_id: str):
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("無効なメッセージIDです。", ephemeral=True)
        return

    try:
        reactions = await asyncio.to_thread(_fetch_reactions_sync, msg_id)
    except Exception as e:
        logger.error(f"Error fetching reactions for message_id={msg_id}: {e}")
        await interaction.response.send_message("リアクション取得中にエラーが発生しました。", ephemeral=True)
        return

    if reactions is None:
        await interaction.response.send_message("DBにそのメッセージが存在しません。", ephemeral=True)
        return

    if not reactions:
        await interaction.response.send_message("リアクションはありません。", ephemeral=True)
    else:
        embed = discord.Embed(
            title=f"Message ID: {msg_id} のリアクション情報",
            color=0x00FF00
        )
        for emoji_id, user_ids in reactions.items():
            try:
                emoji_obj = bot.get_emoji(int(emoji_id))
                if emoji_obj:
                    emoji_str = str(emoji_obj)
                else:
                    emoji_str = f"UnknownEmoji({emoji_id})"
            except ValueError:
                emoji_str = f"InvalidEmojiID({emoji_id})"

            embed.add_field(
                name=emoji_str,
                value=f"{len(user_ids)} 人: {user_ids}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="save", description="既存のメッセージのリアクションをデータベースに保存します。")
async def save_command(interaction: discord.Interaction):
    try:
        logger.info(f"/save command invoked by user_id={interaction.user.id}")
        await interaction.response.send_message("リアクションの移行を開始します。しばらくお待ちください...", ephemeral=True)
        asyncio.create_task(run_db_save(interaction))
    except Exception as e:
        logger.error(f"Unexpected error in save_command: {e}", exc_info=True)
        if not interaction.response.is_done():
            await interaction.response.send_message("リアクションの移行中に予期しないエラーが発生しました。", ephemeral=True)
        else:
            await interaction.followup.send("リアクションの移行中に予期しないエラーが発生しました。", ephemeral=True)


async def run_db_save(interaction: discord.Interaction):
    try:
        logger.info("run_db_save task started.")
        channel = bot.get_channel(THREAD_ID)
        if channel is None:
            await interaction.followup.send("指定したTHREAD_IDのチャンネルが見つかりませんでした。", ephemeral=True)
            logger.error("Specified THREAD_ID channel not found.")
            return

        all_messages = []
        try:
            async for msg in channel.history(limit=None):
                all_messages.append(msg)
            logger.debug(f"Fetched {len(all_messages)} messages.")
        except discord.HTTPException as e:
            logger.error(f"Error fetching message history for migration: {e}")
            await interaction.followup.send("メッセージ履歴の取得中にエラーが発生しました。", ephemeral=True)
            return

        success_count = 0
        for message in all_messages:
            await ensure_message_in_db(message)
            try:
                fetched_msg = await channel.fetch_message(message.id)
                for reaction in fetched_msg.reactions:
                    if isinstance(reaction.emoji, discord.Emoji):
                        if reaction.emoji.id not in REACTIONS.values():
                            continue
                        emoji_id = reaction.emoji.id
                    else:
                        continue
                    async for user in reaction.users():
                        if user.id == bot.user.id:
                            continue
                        await update_reactions_in_db(message.id, emoji_id, user.id, add=True)
                success_count += 1
                await asyncio.sleep(0.1)
            except discord.HTTPException as e:
                logger.error(f"Error fetching reactions for message_id={message.id}: {e}")

        await interaction.followup.send(
            f"リアクションの移行が完了しました。{success_count} 件のメッセージを処理しました。",
            ephemeral=True
        )
        logger.info(f"/save command completed successfully. Processed {success_count} messages.")
    except Exception as e:
        logger.error(f"Unexpected error in run_db_save task: {e}", exc_info=True)
        await interaction.followup.send("リアクションの移行中に予期しないエラーが発生しました。", ephemeral=True)


########################
# リアクションイベント
########################
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    logger.info(f"on_raw_reaction_add fired: emoji={payload.emoji}, user_id={payload.user_id}, message_id={payload.message_id}")

    if payload.user_id == bot.user.id:
        return

    if isinstance(payload.emoji, discord.Emoji):
        if payload.emoji.id not in REACTIONS.values():
            return
    else:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        logger.info("channel is None, cannot process reaction.")
        return

    message = await safe_fetch_message(channel, payload.message_id)
    if not message:
        logger.info(f"message_id={payload.message_id} not found in channel.")
        return

    await ensure_message_in_db(message)
    await update_reactions_in_db(payload.message_id, payload.emoji.id, payload.user_id, add=True)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    logger.info(f"on_raw_reaction_remove fired: emoji={payload.emoji}, user_id={payload.user_id}, message_id={payload.message_id}")

    if payload.user_id == bot.user.id:
        return

    if isinstance(payload.emoji, discord.Emoji):
        if payload.emoji.id not in REACTIONS.values():
            return
    else:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        logger.info("channel is None, cannot process reaction removal.")
        return

    message = await safe_fetch_message(channel, payload.message_id)
    if not message:
        logger.info(f"message_id={payload.message_id} not found in channel.")
        return

    await ensure_message_in_db(message)
    await update_reactions_in_db(payload.message_id, payload.emoji.id, payload.user_id, add=False)


########################
# メッセージイベント
########################
farewell_messages = [
    "{mention} いい夢見なっつ！",
    "{mention} 夢で会おうなっつ！",
    "{mention} ちゃんと布団で寝なっつ！",
    "{mention} また起きたら来てくれよなっつ！"
]

target_channel_ids = [1282323693502070826, 1300417181690892288]


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id in target_channel_ids and message.mentions:
        for user in message.mentions:
            if user.voice and user.voice.channel:
                try:
                    await user.move_to(None)
                    farewell_message = random.choice(farewell_messages).format(mention=user.mention)
                    await message.channel.send(farewell_message)
                except discord.Forbidden:
                    await message.channel.send(f"{user.mention}を切断する権限がありません。")
                except discord.HTTPException as e:
                    await message.channel.send(f"エラーが発生しました: {e}")

    if message.content == "バルス":
        now = datetime.utcnow()
        deleted_count = 0
        async for msg in message.channel.history(limit=None, after=now - timedelta(hours=1)):
            if msg.author.id == message.author.id:
                try:
                    await msg.delete()
                    deleted_count += 1
                    if deleted_count % 10 == 0:
                        await asyncio.sleep(0.5)
                except (discord.Forbidden, discord.HTTPException) as e:
                    await message.channel.send(f"メッセージ削除中にエラーが発生しました: {e}")
                    logger.error(f"エラー発生: {e}")
                    return

        await message.channel.send(
            f"過去1時間以内にあなたが送信したメッセージを{deleted_count}件削除しました。",
            delete_after=2
        )
        logger.info(f"{deleted_count}件のメッセージを削除しました。")

    await bot.process_commands(message)


########################
# メッセージ履歴同期タスク
########################
@tasks.loop(minutes=5)
async def save_all_messages_to_db_task():
    await save_all_messages_to_db()


async def save_all_messages_to_db():
    channel = bot.get_channel(THREAD_ID)
    if channel is None:
        logger.error("指定したTHREAD_IDのチャンネルが見つかりませんでした。")
        return

    all_messages = []
    last_msg = None
    batch_size = 50
    try:
        while True:
            batch = []
            async for msg in channel.history(limit=batch_size, before=last_msg):
                batch.append(msg)
            if not batch:
                break
            all_messages.extend(batch)
            last_msg = batch[-1]
            await asyncio.sleep(1.0)

        if all_messages:
            await bulk_save_messages_to_db(all_messages)
        logger.info(f"Saved total {len(all_messages)} messages to the database (paging).")
    except discord.HTTPException as e:
        logger.error(f"Error fetching message history in paging: {e}")


async def bulk_save_messages_to_db(messages):
    if not messages:
        return
    try:
        await asyncio.to_thread(_bulk_save_messages_to_db_sync, messages)
    except Exception as e:
        logger.error(f"Error during bulk save of messages: {e}")


def _bulk_save_messages_to_db_sync(messages):
    conn = get_db_connection()
    if not conn:
        return
    try:
        data = []
        for message in messages:
            data.append((message.id, message.channel.id, message.author.id, message.content))
            logger.debug(f"Bulk saving message_id={message.id} to DB without reactions.")

        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO messages (message_id, thread_id, author_id, content)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
            """, data)
            conn.commit()

        logger.info(f"Bulk inserted {len(messages)} messages without reactions.")
    except Error as e:
        logger.error(f"Error during bulk insert: {e}")
    finally:
        release_db_connection(conn)


########################
# Bot起動
########################
if DISCORD_TOKEN:
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error starting the bot: {e}")
        if db_pool:
            db_pool.closeall()
            logger.info("Closed all database connections.")
else:
    logger.error("DISCORD_TOKEN が設定されていません。")
