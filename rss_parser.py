import feedparser
import asyncio
import uuid
from db_operations import fetch_rss_sources

async def fetch_rss_feed(url):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, feedparser.parse, url)

async def fetch_all_rss_sources(db_pool):
    sources = await fetch_rss_sources(db_pool)
    tasks = [fetch_rss_feed(source[1]) for source in sources]
    feeds = await asyncio.gather(*tasks)
    
    rss_items = []
    for source_id, feed in zip([s[0] for s in sources], feeds):
        for entry in feed.entries:
            rss_items.append({
                'source_id': source_id,
                'guid': str(uuid.uuid4()),  # 生成一个新的UUID
                'url': entry.link,
                'title': entry.title,
                'content': entry.get('content', [{'value': entry.get('summary', '')}])[0]['value'],
                'published_at': entry.get('published'),
            })
    
    return rss_items