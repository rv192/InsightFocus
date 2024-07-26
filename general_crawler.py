import json
import re
import httpx
import trafilatura
from urllib.parse import urlparse
from typing import Dict, Union, Callable
from gne import GeneralNewsExtractor
import logging

class GeneralCrawler:
    def __init__(self):
        # 特定域名的处理器映射，可以根据需要扩展
        self.scraper_map = {
            "mp.weixin.qq.com": self.wechat_handler
            # TODO: 可以添加更多特定域处理器
        }

    def info(self):
        logging.info("Test")

    def fetch_html(self, url: str) -> Union[str, None]:
        header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/604.1 Edg/112.0.100.0'}

        """获取网页HTML内容"""
        try:
            response = httpx.get(url, headers=header, timeout=30)
            response.raise_for_status()
            logging.info(f"Successfully fetched HTML content from {url}")
            return response.text
        except httpx.RequestError as exc:
            logging.error(f"HTTP request error: {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            logging.error(f"HTTP status error: {exc}")
            return None

    def extract_content(self, html_content: str, url: str) -> Dict[str, str]:
        """使用Trafilatura提取网页内容"""
        result = {
            "title": "",
            "author": "",
            "publish_date": "",
            "content": html_content,
            "plain_content": ""
        }
        try:
            extractor = GeneralNewsExtractor()
            result = extractor.extract(html_content, noise_node_list=['//div[@class="comment-list"]'])
            downloaded = trafilatura.extract(html_content, url=url, output_format = "json", with_metadata=True, include_comments=False, include_images=False)
            json.loads(downloaded)
            if downloaded:
                result['title'] = downloaded.get('title', '')
                result['author'] = downloaded.get('author', '')
                result['publish_date'] = downloaded.get('date', '')
                result['plain_content'] = downloaded.get('text', '')
                logging.info("Trafilatura：内容提取成功")
            else:
                logging.warning("Trafilatura： 内容提取失败")
        except Exception as exc:
            logging.error(f"Trafilatura extraction error: {exc}")
        return result

    def wechat_handler(self, html_content: str) -> Dict[str, str]:
        """特定域名的处理器示例"""
        # TODO: 针对mp.weixin.qq.com的自定义处理逻辑
        logging.info("Using specific handler for mp.weixin.qq.com")
        return {"title": "Example Title", "author": "Example Author", "publish_date": "2024-07-25", "extracted_content": "Example Content"}

    def llm_fallback(self, html_content: str, url: str) -> Dict[str, str]:
        """LLM兜底处理逻辑"""
        logging.info("Using LLM fallback for content extraction")
        return {
            "title": "Fallback Title",
            "author": "Fallback Author",
            "publish_date": "Fallback Date",
            "plain_content": "Fallback Content"
        }

    def crawl(self, url: str) -> Dict[str, Union[int, str, dict]]:
        """主抓取流程"""

        # 初始化缺省JSON对象
        result = {
            "status_code": 200,  # 默认状态码为200（成功）
            "error_message": "",
            "original_html": "",
            "plain_content": "",
            "title": "",
            "author": "",
            "publish_date": ""
        }

        # 获取HTML内容
        html_content = self.fetch_html(url)
        if not html_content:
            result["status_code"] = -1  # HTML获取失败
            result["error_message"] = "Failed to fetch HTML content"
            return result

        result["original_html"] = html_content

        # 确定域名并检查是否有特定的处理器
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        base_url = f"{parsed_url.scheme}://{domain}"

        handler = self.scraper_map.get(domain, None)

        if handler:
            extracted_data = handler(html_content)
        else:
            extracted_data = self.extract_content(html_content, url)

        # TODO: 如果提取失败，使用LLM兜底
        if not extracted_data['plain_content']:
            extracted_data = self.llm_fallback(html_content, url)
            result["status_code"] = 200  

        result.update(extracted_data)
        return result

def main():
    # 示例HTML内容
    your_sample_html = """
<html>
        <head>
            <title>示例网页标题</title>
        </head>
        <body>
            <h1>这是一个示例标题</h1>
            <p>这是示例内容，作者：张三，发布日期：2024-07-26。</p>
        </body>
    </html>
"""

    extractor = GeneralNewsExtractor()
    result = extractor.extract(your_sample_html)


    downloaded = trafilatura.extract(your_sample_html, url="https://mp.weixin.qq.com/s/fkRQjRkVLp1JPTaE141tZQ", output_format = "json", with_metadata=True, include_comments=False, include_images=True)
    re2 = json.loads(downloaded)
    
    try:
        r2 = json.loads(downloaded)
    except json.JSONDecodeError as e:
        json_match = re.search(r'\{.*\}', downloaded, re.DOTALL)
        if json_match:
            r2 = json.loads(json_match.group(0))
        else:
            logging.error(f"无法解析 AI 响应为 JSON: {downloaded}")
    except Exception as e:
        logging.error(e)

if __name__ == "__main__":
    main()
