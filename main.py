import asyncio
import logging

from dotenv import load_dotenv
from rss_parser import fetch_all_rss_sources
from content_processor import process_rss_items
from db_operations import get_db_pool

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main(): 
    db_pool = None
    try:
        db_pool = await get_db_pool()
        if db_pool is None:
            raise Exception("Failed to create database pool")
        
        logging.info("Database pool created")
        rss_items = await fetch_all_rss_sources(db_pool)
        logging.info(f"Fetched {len(rss_items)} RSS items")
        await process_rss_items(db_pool, rss_items)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        if db_pool:
            try:
                # 检查 close 方法是否为协程
                if asyncio.iscoroutinefunction(db_pool.close):
                    await db_pool.close()
                else:
                    db_pool.close()
                logging.info("Database pool closed")
            except Exception as e:
                logging.error(f"Error closing database pool: {e}")

if __name__ == "__main__":
    asyncio.run(main())