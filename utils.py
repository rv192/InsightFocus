import hashlib
import logging
from dateutil import parser

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