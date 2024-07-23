import asyncio
import logging
from dotenv import load_dotenv
from rss_parser import fetch_all_rss_sources
from content_processor import process_rss_items
from db_operations import get_db_pool
from focus_processor import run_focus_processing  # 导入新的用户关注处理函数

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_and_process_rss(db_pool):
    rss_items = await fetch_all_rss_sources(db_pool)
    logging.info(f"Fetched {len(rss_items)} RSS items")
    await process_rss_items(db_pool, rss_items)

async def main():
    db_pool = None
    try:
        db_pool = await get_db_pool()
        if db_pool is None:
            raise Exception("Failed to create database pool")
        
        logging.info("Database pool created")

        while True:
            print("\n请选择操作：")
            print("1. 抓取并处理RSS内容")
            print("2. 处理用户关注")
            print("3. 退出")
            
            choice = input("请输入选项（1/2/3）: ")

            if choice == '1':
                await fetch_and_process_rss(db_pool)
            elif choice == '2':
                await run_focus_processing(db_pool)
            elif choice == '3':
                print("程序退出")
                break
            else:
                print("无效选项，请重新选择")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        if db_pool:
            try:
                if asyncio.iscoroutinefunction(db_pool.close):
                    await db_pool.close()
                else:
                    db_pool.close()
                logging.info("Database pool closed")
            except Exception as e:
                logging.error(f"Error closing database pool: {e}")

if __name__ == "__main__":
    asyncio.run(main())