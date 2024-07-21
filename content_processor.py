import logging

from bs4 import BeautifulSoup

from utils import hash_text, detect_language, estimate_read_time
from ai_processor import CATEGORIES, process_content, categorize_tags
from db_operations import with_transaction, process_rss_item_transaction, check_existing_article

async def process_rss_items(db_pool, rss_items):
    for item in rss_items:
        logging.info(f"-----------------------------------------------")
        logging.info(f"正在处理->{item['url']}")
        logging.info(f"标题：{item['title']}")
        
        url_hash = hash_text(item['url'])

        # 检查URL是否已存在
        existing_article = await with_transaction(db_pool, check_existing_article, url_hash=url_hash)
        if existing_article:
            logging.info(f"文章URL已存在，跳过：{item['url']}")
            continue

        original_plain_content = extract_plain_content(item['content'])
        if not original_plain_content:
            logging.warning(f"无法提取纯文本内容，项目：{item['url']}")
            continue
        
        content_hash = hash_text(original_plain_content)
        
        # 检查内容是否已存在
        existing_article = await with_transaction(db_pool, check_existing_article, content_hash=content_hash)
        if existing_article:
            logging.info(f"文章内容已存在，跳过：{item['url']}")
            continue
        
        try:
            ai_result = await process_content(item['title'], original_plain_content)
            
            if ai_result is None:
                logging.warning(f"AI处理失败，项目：{item['url']}。使用原始内容。")
                processed_plain_content = original_plain_content
                summary = ""
                tags = []
            else:
                logging.info(f"AI处理完成，项目：{item['url']}")
                processed_plain_content = ai_result['processed_content'] or original_plain_content
                summary = ai_result['summary']
                tags = ai_result['tags']

            categorized_tags = await categorize_tags(tags, item['title'], summary)

            language = detect_language(processed_plain_content)
            read_time = estimate_read_time(processed_plain_content)                

            for tag in categorized_tags:
                category_name = next((category[1] for category in CATEGORIES if category[0] == tag['category_id']), None)
                if category_name:
                    logging.info(f"标签名称：{tag['name']}, 分类ID：{tag['category_id']}, 分类名称：{category_name}")
                else:
                    logging.warning(f"未找到分类ID：{tag['category_id']}对应的分类名称")

            # 在一个事务中处理整个RSS项目
            await with_transaction(
                db_pool, 
                process_rss_item_transaction, 
                item, 
                original_plain_content, 
                url_hash, 
                content_hash, 
                processed_plain_content, 
                summary, 
                categorized_tags, 
                language, 
                read_time
            )

        except Exception as e:
            logging.error(f"处理项目时出错 {item['url']}: {str(e)}")
            
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