import logging

from agents.userFocusAgent import UserFocusAgent
from db_operations import with_transaction, get_recent_articles, get_user_focuses, add_to_focused_contents

async def process_user_focuses(db_pool):
    try:
        recent_articles = await with_transaction(db_pool, lambda cur: get_recent_articles(cur, hours=24))
        logging.info(f"获取到 {len(recent_articles)} 篇最近的文章")

        # 获取到所有的用户名单
        user_ids = await get_all_users(db_pool)
        
        for user_id in user_ids:
            await process_user_focus(db_pool, user_id, recent_articles)

    except Exception as e:
        logging.error(f"处理用户关注内容时出错: {str(e)}")

async def process_user_focus(db_pool, user_id, recent_articles):
    logging.info(f"处理用户 {user_id} 的关注内容")

    user_focuses = await with_transaction(db_pool, get_user_focuses, user_id)
    
    for article in recent_articles:
        for focus in user_focuses:
            logging.info(f"-----------------------------------------------------------------------")
            logging.info(f"开始处理URL：{article['url']}")
            logging.info(f"文章标题：{article['title']}")
            is_relevant = await UserFocusAgent().judge_article_relevance(article, focus['content'])
            
            if is_relevant:
                await with_transaction(
                    db_pool,
                    add_to_focused_contents,
                    user_id,
                    article['id'],
                    focus['id']
                )
                logging.info(f"文章 {article['id']} 与用户 {user_id} 的关注 {focus['id']} 相关，已添加到关注清单")

async def get_all_users(db_pool):
    async def fetch_users(cur):
        await cur.execute("SELECT id FROM rssUsers")
        return await cur.fetchall()

    users = await with_transaction(db_pool, fetch_users)
    return [user[0] for user in users]

async def run_focus_processing(db_pool):
    logging.info("开始运行关注内容批处理")
    try:
        await process_user_focuses(db_pool)
        logging.info("关注内容批处理完成")
    except Exception as e:
        logging.error(f"关注内容批处理过程中出错: {str(e)}")