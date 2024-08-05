import logging
import os
import aiomysql
from dotenv import load_dotenv
from datetime import datetime, timedelta

from conf.consts import GENRES, TOPICS
from utils import parse_datetime

load_dotenv()

async def get_db_pool():
    try:
        logging.info("Attempting to create database pool...")
        pool = await aiomysql.create_pool(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            db=os.getenv('DB_NAME'),
            autocommit=True
        )
        logging.info("Database pool created successfully")
        return pool
    except Exception as e:
        logging.error(f"Error creating database pool: {e}")
        raise

async def with_transaction(pool, func, *args, **kwargs):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                result = await func(cur, *args, **kwargs)
                await conn.commit()
                return result
            except Exception as e:
                await conn.rollback()
                logging.error(f"Transaction failed: {str(e)}")
                raise

async def check_existing_article(cur, url_hash=None, html_hash=None):
    if url_hash:
        await cur.execute("SELECT id FROM articles WHERE url_hash = %s", (url_hash,))
    elif html_hash:
        await cur.execute("SELECT id FROM articles WHERE html_hash = %s", (html_hash,))
    else:
        return None
    return await cur.fetchone()

async def insert_article(cur, article_data):
    query = """
    INSERT INTO articles (guid, source_id, genre_id, topic_id, url, url_hash, title, original_html, plain_content, 
                          html_hash, published_at, fetched_at, summary, language, read_time, last_updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    original_html = VALUES(original_html),
    plain_content = VALUES(plain_content),
    html_hash = VALUES(html_hash),
    fetched_at = VALUES(fetched_at),
    summary = VALUES(summary),
    language = VALUES(language),
    read_time = VALUES(read_time),
    last_updated_at = VALUES(last_updated_at),
    topic_id = VALUES(topic_id),
    genre_id = VALUES(genre_id)
    """
    values = [article_data.get(key) for key in [
        'guid', 'source_id', 'genre_id', 'topic_id', 'url', 'url_hash', 'title', 'original_html', 'plain_content',
        'html_hash', 'published_at', 'fetched_at', 'summary', 'language', 'read_time'
    ]]
    values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))  # last_updated_at
    await cur.execute(query, tuple(values))
    return cur.lastrowid

async def insert_tags(cur, article_id, tags):
    for tag in tags:
        # 检查标签是否存在
        await cur.execute("SELECT id FROM tags WHERE name = %s", (tag,))
        result = await cur.fetchone()
        
        if result:
            tag_id = result[0]
        else:
            # 如果标签不存在，则插入
            await cur.execute("INSERT INTO tags (name) VALUES (%s)", (tag,))
            tag_id = cur.lastrowid
        
        # 插入文章-标签关联
        await cur.execute("INSERT IGNORE INTO article_tags (article_id, tag_id) VALUES (%s, %s)", (article_id, tag_id))

async def update_rss_source_last_fetched(cur, source_id):
    await cur.execute("""
        UPDATE rssSources
        SET last_fetched_at = NOW()
        WHERE id = %s
    """, (source_id,))

async def process_rss_item_transaction(cur, item, url_hash, html_hash, plain_content, summary, tags, genre_id, topic_id, language, read_time):
    published_at = parse_datetime(item['published_at'])
    if not published_at:
        logging.error(f"解析published_at日期失败，项目：{item['url']}")
        return

    article_data = {
        'guid': item['guid'],
        'source_id': item['source_id'],
        'genre_id': genre_id,
        'topic_id': topic_id,
        'url': item['url'],
        'url_hash': url_hash,
        'title': item['title'],
        # 'original_html': item['original_html'],
        'original_html': '',
        'plain_content': plain_content,
        'html_hash': html_hash,
        'published_at': published_at,
        'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': summary,
        'language': language,
        'read_time': read_time
    }
    
    article_id = await insert_article(cur, article_data)
    
    if article_id:
        logging.info(f"文章已插入，ID：{article_id}")
        await insert_tags(cur, article_id, tags)
        logging.info(f"标签已插入，文章ID：{article_id}")
        await update_rss_source_last_fetched(cur, item['source_id'])
    else:
        logging.warning(f"插入文章失败：{item['url']}")

async def fetch_rss_sources(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id, url FROM rssSources")
            return await cur.fetchall()
        
async def get_recent_articles(cur, hours=24):
    """获取最近24小时内入库的文章"""
    query = """
    SELECT id, genre_id, topic_id, title, plain_content, summary, url
    FROM articles
    WHERE fetched_at >= %s
    """
    time_threshold = datetime.now() - timedelta(hours=hours)
    await cur.execute(query, (time_threshold,))
    results = await cur.fetchall()
    # 创建类型和分类的映射字典
    genre_mapping = {t[0]: t[1] for t in GENRES}
    topic_mapping = {c[0]: c[1] for c in TOPICS}

    # 处理查询结果，并添加类型和分类信息
    articles = [
        {
            'id': row[0],
            'genre_id': row[1],
            'topic_id': row[2],
            'title': row[3],
            'plain_content': row[4],
            'summary': row[5],
            'genre': genre_mapping.get(row[1], '未知类型'),
            'topic': topic_mapping.get(row[2], '未知分类'),
            'url': row[6]
        }
        for row in results
    ]
    
    return articles

async def get_user_focuses(cur, user_id):
    """获取用户的关注内容描述"""
    query = """
    SELECT id, content
    FROM userFocuses
    WHERE user_id = %s
    """
    await cur.execute(query, (user_id,))
    results = await cur.fetchall()
    return [
        {
            'id': row[0],
            'content': row[1]
        }
        for row in results
    ]

async def add_to_focused_contents(cur, user_id, article_id, focus_id):
    """将符合用户关注的文章添加到关注清单中"""
    query = """
    INSERT INTO focusedContents (user_id, article_id, focus_id, created_at)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE created_at = VALUES(created_at)
    """
    await cur.execute(query, (user_id, article_id, focus_id, datetime.now()))