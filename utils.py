import hashlib
import logging
import os
from dateutil import parser

from dotenv import load_dotenv
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

def hash_text(text):
    if text is None:
        return None
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def detect_language(text):
    try:
        lang = detect(text)
        if lang == 'zh-cn':
            return 'zh-cn'
        elif lang == 'zh-tw':
            return 'zh-tw'
        elif lang == 'en':
            return 'en-us'
        else:
            return f'{lang}-{lang}'
    except LangDetectException:
        return 'und-und'

def estimate_read_time(content):
    words = len(content)
    return round(words / 200)  # 假设平均阅读速度为每分钟200字

def parse_datetime(dt_string):
    if not dt_string:
        return None
    try:
        dt = parser.parse(dt_string)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        logging.warning(f"无法解析日期时间字符串: {dt_string}")
        return None
    
def get_env(key, default=None, var_type=str):
    load_dotenv()
    value = os.getenv(key, default)
    if value is None:
        return default
        
    if var_type == int:
        return int(value)
    elif var_type == float:
        return float(value)
    elif var_type == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    return value