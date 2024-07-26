from datetime import datetime
import logging
import feedparser
import asyncio
import uuid
import httpx
from db_operations import fetch_rss_sources
from lxml import etree

async def fetch_rss_feed(url):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            parser = etree.XMLParser(recover=True)
            tree = etree.fromstring(response.content, parser=parser)
            rss_data = etree.tostring(tree)
            return feedparser.parse(rss_data)
        except Exception as e:
            logging.error(f"Error fetching or parsing {url}: {e}")
            return feedparser.FeedParserDict(entries=[])

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
                'published_at': entry.get('published',entry.get('updated', datetime.now())),
            })
    
    return rss_items
