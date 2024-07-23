import os
import json
import logging
import re
from string import Template
import functools
import asyncio
from typing import Any, Dict

import yaml
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 常量定义
CATEGORIES = [
    (0, '待分类'),
    (1, '新闻与时事'),
    (2, '科技与创新'),
    (3, '商业与金融'),
    (4, '健康与医疗'),
    (5, '环境与可持续发展'),
    (6, '文化与艺术'),
    (7, '教育与学术'),
    (8, '体育与娱乐'),
    (9, '生活方式'),
    (10, '科学与探索'),
    (11, '社会问题'),
    (12, '历史与观点')
]

class ConfigError(Exception):
    pass

class AIAPIError(Exception):
    pass

def async_retry(max_tries=3, delay_seconds=1):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tries = 0
            while tries < max_tries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    tries += 1
                    if tries == max_tries:
                        logging.error(f"函数 {func.__name__} 在 {max_tries} 次尝试后失败: {str(e)}")
                        raise
                    logging.warning(f"函数 {func.__name__} 失败，正在重试 ({tries}/{max_tries}): {str(e)}")
                    await asyncio.sleep(delay_seconds)
        return wrapper
    return decorator

def load_config():
    load_dotenv()
    with open(os.path.join('./conf', 'prompts.yaml'), 'r', encoding='utf-8') as file:
        prompts = yaml.safe_load(file)
    return prompts

PROMPTS = load_config()

def create_ai_client(config_name):
    try:
        config = json.loads(os.getenv(f'{config_name}_CONFIG'))
        return AsyncOpenAI(api_key=config['api_key'], base_url=config['base_url'])
    except (json.JSONDecodeError, KeyError) as e:
        raise ConfigError(f"Invalid configuration for {config_name}: {str(e)}")

@async_retry(max_tries=3, delay_seconds=2)
async def call_ai_api(client, model, system_message, user_message):
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                logging.error(f"无法解析 AI 响应为 JSON: {content}")
                raise ValueError("Invalid JSON response from AI")
    except Exception as e:
        logging.error(f"AI API 调用失败: {str(e)}")
        raise

async def process_content(title, content):
    client = create_ai_client('CONTENT_PROCESSOR')
    config = json.loads(os.getenv('CONTENT_PROCESSOR_CONFIG'))
    
    prompt_template = PROMPTS.get('process_content')
    if not prompt_template:
        raise ConfigError("process_content prompt not found")
    
    prompt = Template(prompt_template).safe_substitute(title=title, content=content)
    
    try:
        result = await call_ai_api(client, config['model'], PROMPTS.get('process_content_system', ""), prompt)
        return {
            'processed_content': result.get('processed_content', ''),
            'summary': result.get('summary', ''),
            'tags': result.get('tags', [])
        }
    except AIAPIError as e:
        logging.error(f"Content processing failed: {str(e)}")
        return {'processed_content': '', 'summary': '', 'tags': []}

async def categorize_article(title, summary, tags):
    client = create_ai_client('ARTICLE_CATEGORIZER')
    config = json.loads(os.getenv('ARTICLE_CATEGORIZER_CONFIG'))
    categories_info = "\n".join(f"{id}. {name}" for id, name in CATEGORIES)
    
    prompt = Template(PROMPTS['categorize_article']).safe_substitute(
        categories_info=categories_info, title=title, summary=summary, tags=', '.join(tags)
    )
    
    try:
        result = await call_ai_api(client, config['model'], PROMPTS['categorize_article_system'], prompt)
        return result.get('category_id')
    except AIAPIError as e:
        logging.error(f"Article categorization failed: {str(e)}")
        return None

async def judge_article_relevance(article, focus) -> bool:
    client = create_ai_client('FOCUS_MATCHER')
    config = json.loads(os.getenv('FOCUS_MATCHER_CONFIG'))
    
    prompt_template = PROMPTS.get('judge_article_relevance')
    if not prompt_template:
        raise ConfigError("judge_article_relevance prompt not found")
    
    prompt = Template(prompt_template).safe_substitute(
        article_title=article['title'],
        article_summary=article['summary'],
        focus_content=focus
    )
    
    try:
        result = await call_ai_api(client, config['model'], PROMPTS.get('judge_article_relevance_system', ""), prompt)

        isPass = result.get('is_relevant')
        reason = result.get('reason')
        logging.info(f"{isPass}：{reason}")

        return result.get('is_relevant', False)
    except AIAPIError as e:
        logging.error(f"Article relevance judgment failed: {str(e)}")
        return False