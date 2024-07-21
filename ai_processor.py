import os
import json
import logging
import re
from collections import defaultdict
from string import Template

import yaml
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 常量定义
CATEGORIES = [
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
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        raise AIAPIError("Failed to parse JSON from API response")
    except Exception as e:
        raise AIAPIError(f"AI API call failed: {str(e)}")

async def process_content(title, content):
    client = create_ai_client('CONTENT_PROCESSOR')
    config = json.loads(os.getenv('CONTENT_PROCESSOR_CONFIG'))
    
    prompt_template = PROMPTS.get('process_content')
    if not prompt_template:
        raise ConfigError("process_content prompt not found")
    
    prompt = Template(prompt_template).safe_substitute(title=title, content=content[:3500])
    
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

async def categorize_tags(tags, title, summary):
    if not tags:
        return []
    
    client = create_ai_client('TAG_CATEGORIZER')
    config = json.loads(os.getenv('TAG_CATEGORIZER_CONFIG'))
    categories_info = "\n".join(f"{id}. {name}" for id, name in CATEGORIES)
    
    prompt = Template(PROMPTS['categorize_tags']).safe_substitute(
        categories_info=categories_info, title=title, summary=summary, tags=', '.join(tags)
    )
    
    try:
        result = await call_ai_api(client, config['model'], PROMPTS['categorize_tags_system'], prompt)
        return result.get('tags', [])
    except AIAPIError as e:
        logging.error(f"Tag categorization failed: {str(e)}")
        return []