import logging

from bs4 import BeautifulSoup

from agents.summaryAgent import SummaryAgent
from conf.consts import GENRES, TOPICS
from general_crawler import GeneralCrawler
from utils import hash_text, detect_language, estimate_read_time
from db_operations import with_transaction, process_rss_item_transaction, check_existing_article

async def process_rss_items(db_pool, rss_items):
    for item in rss_items:
        logging.info(f"-----------------------------------------------")

        url = item.get('url')
        title = item['title']
        
        logging.info(f"正在处理->{url}")
        logging.info(f"标题：{title}")
        
        url_hash = hash_text(url)

        # 检查URL是否已存在
        existing_article = await with_transaction(db_pool, check_existing_article, url_hash=url_hash)
        if existing_article:
            logging.info(f"文章URL已存在，跳过：{url}")
            continue

        crawler = GeneralCrawler()
        resultCrawler =  await crawler.crawl_async(url)
        original_html = resultCrawler['content']
        item['original_html'] = original_html
        plain_content = resultCrawler['plain_content']

        if resultCrawler.get('status_code') != 200:
            continue

        html_hash = hash_text(resultCrawler.get('content'))
        
        # 检查内容是否已存在
        existing_article = await with_transaction(db_pool, check_existing_article, html_hash=html_hash)
        if existing_article:
            logging.info(f"文章内容已存在，跳过：{url}")
            continue
        
        try:
            ai_result = await SummaryAgent().process_content(title, plain_content)
            
            if ai_result is None:
                logging.warning(f"AI摘要处理失败，项目：{url}。使用标题代替摘要。")
                summary = title
                tags = []
            else:
                logging.info(f"AI摘要处理完成，项目：{url}")
                summary = ai_result.get('summary', "")
                tags = ai_result.get('tags', [])
                logging.info(f"Summary:\r\n{summary}")
                logging.info(f"Tags: {', '.join(tags)}")


            # 使用新的classify_article函数
            classifiedInfo = await SummaryAgent().classify_article(title, summary, tags)

            genre_id = 0  # 默认题材ID
            topic_id = 0  # 默认主题ID

            if classifiedInfo:
                genre_id = classifiedInfo.get('genre_id', 0)
                topic_id = classifiedInfo.get('topic_id', 0)

                # 定义一个辅助函数来获取名称
                def get_name(id, id_list):
                    return next((name for _id, name, _ in id_list if _id == id), None)

                # 获取类型名称
                genre_name = get_name(genre_id, GENRES)
                if genre_name:
                    logging.info(f"文章题材ID：{genre_id}, 题材：{genre_name}")
                else:
                    logging.warning(f"未找到题材ID：{genre_id}对应的题材名，项目：{url}")

                # 获取分类名称
                topic_name = get_name(topic_id, TOPICS)
                if topic_name:
                    logging.info(f"文章主题ID：{topic_id}, 主题名：{topic_name}")
                else:
                    logging.warning(f"未找到主题ID：{topic_id}对应的主题名称，项目：{url}")
            else:
                logging.warning(f"文章分类失败，项目：{url}。使用默认分类。")

            language = detect_language(original_html)
            read_time = estimate_read_time(plain_content)

            # 在一个事务中处理整个RSS项目
            await with_transaction(
                db_pool, 
                process_rss_item_transaction, 
                item, 
                url_hash, 
                html_hash, 
                plain_content, 
                summary, 
                tags, 
                genre_id,
                topic_id,
                language, 
                read_time
            )

        except Exception as e:
            logging.error(f"处理项目时出错 {url}: {str(e)}")
            continue


def extract_plain_content(html_content):
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for script in soup(["script", "style"]):
        script.decompose()
    
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text or None