import os
import json
import logging
import re
from string import Template
import functools
import asyncio

import yaml
from openai import AsyncOpenAI
from dotenv import load_dotenv

class ConfigError(Exception):
    pass

class IntelligentAPIError(Exception):
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
    return decorator    # ... (保持原有实现不变)

def load_config():
    load_dotenv()
    with open(os.path.join('./conf', 'prompts.yaml'), 'r', encoding='utf-8') as file:
        prompts = yaml.safe_load(file)
    return prompts

PROMPTS = load_config()

class BaseAgent:
    def __init__(self, config_name):
        self.client = self.create_ai_client(config_name)
        self.config = json.loads(os.getenv(f'{config_name}_CONFIG'))

    def create_ai_client(self, config_name):
        try:
            config = json.loads(os.getenv(f'{config_name}_CONFIG'))
            return AsyncOpenAI(api_key=config['api_key'], base_url=config['base_url'])
        except (json.JSONDecodeError, KeyError) as e:
            raise ConfigError(f"Invalid configuration for {config_name}: {str(e)}")

    @async_retry(max_tries=3, delay_seconds=2)
    async def call_ai_api(self, system_message, user_message):
        try:
            response = await self.client.chat.completions.create(
                model=self.config['model'],
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



