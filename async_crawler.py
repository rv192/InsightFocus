from threading import Lock
from typing import Dict, Union
from urllib.parse import urlparse

from pyppeteer import launch
import httpx
from gne import GeneralNewsExtractor
import trafilatura
import json
import logging

from utils import get_env

class AsyncCrawler:
    _instance = None
    _lock = Lock()
    _browser = None
    _pages = []
    _page_index = 0
    _restart_threshold = 1000
    _page_count = 0
    
    # 从环境变量读取参数值
    PAGE_POOL_SIZE = get_env('PAGE_POOL_SIZE', 10, int)
    _restart_threshold = get_env('BROWSER_RESTART_COUNT', 1000, int)

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.scraper_map = {
            "mp.weixin.qq.com": self.wechat_handler
        }
        self.ajax_domains = ["36kr.com"]

    async def get_browser(self):
        if self._browser is None or self._page_count >= self._restart_threshold:
            await self.close_browser()  # 确保旧的浏览器被关闭
            with self._lock:
                if self._browser is None or self._page_count >= self._restart_threshold:
                    self._browser = await launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
                    self._pages = []
                    for _ in range(self.PAGE_POOL_SIZE):  # 使用PAGE_POOL_SIZE常量
                        page = await self._browser.newPage()
                        self._pages.append(page)
                    self._page_index = 0
                    self._page_count = 0
                    logging.info(f"New browser instance created with {self.PAGE_POOL_SIZE} pages")
        return self._browser

    async def close_browser(self):
        if self._browser:
            for page in self._pages:
                await page.close()
            await self._browser.close()
            self._browser = None
            self._pages = []
            self._page_count = 0
            logging.info("Browser instance and all pages closed")

    async def fetch_with_pyppeteer(self, url: str) -> Union[str, None]:
        await self.get_browser()  # 确保浏览器和页面已初始化
        page = self._pages[self._page_index]
        self._page_index = (self._page_index + 1) % len(self._pages)
        self._page_count += 1
        try:
            await page.goto(url, waitUntil='networkidle0')
            content = await page.content()
            return content
        except Exception as e:
            logging.error(f"Pyppeteer error: {e}")
            return None
        finally:
            logging.debug(f"Page used. Total pages used: {self._page_count}")

    async def fetch_with_httpx(self, url: str) -> Union[str, None]:
        async with httpx.AsyncClient() as client:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                response = await client.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.text
            except httpx.RequestError as e:
                logging.error(f"HTTPX error: {e}")
                return None

    async def fetch_html(self, url: str) -> Union[str, None]:
        domain = urlparse(url).netloc
        if domain in self.ajax_domains:
            return await self.fetch_with_pyppeteer(url)
        else:
            return await self.fetch_with_httpx(url)

    def extract_content(self, html_content: str, url: str) -> Dict[str, str]:
        result = {
            "title": "",
            "author": "",
            "publish_date": "",
            "content": html_content,
            "plain_content": ""
        }
        try:
            extractor = GeneralNewsExtractor()
            gne_result = extractor.extract(html_content, noise_node_list=['//div[@class="comment-list"]'])
            if gne_result:
                result['title'] = gne_result.get('title', '')
                result['author'] = gne_result.get('author', '')
                result['publish_date'] = gne_result.get('publish_time', '')
                result['plain_content'] = gne_result.get('content', '')
                logging.info("GNE: Content extraction successful")
            else:
                logging.warning("GNE: Content extraction failed, trying Trafilatura")

            if not result['plain_content']:
                downloaded = trafilatura.extract(html_content, url=url, output_format="json", with_metadata=True, include_comments=False, include_images=True)
                if downloaded:
                    trafilatura_result = json.loads(downloaded)
                    result['title'] = result['title'] or trafilatura_result.get('title', '')
                    result['author'] = result['author'] or trafilatura_result.get('author', '')
                    result['publish_date'] = result['publish_date'] or trafilatura_result.get('date', '')
                    result['plain_content'] = result['plain_content'] or trafilatura_result.get('text', '')
                    logging.info("Trafilatura: Content extraction successful")
                else:
                    logging.warning("Trafilatura: Content extraction failed")

        except Exception as exc:
            logging.error(f"Content extraction error: {exc}")
        
        return result

    def wechat_handler(self, html_content: str) -> Dict[str, str]:
        logging.info("Using specialized scraper for domain: mp.weixin.qq.com")
        # 实现微信文章的特定抓取逻辑
        return {
            "title": "Example WeChat Title",
            "author": "Example WeChat Author",
            "publish_date": "2024-07-25",
            "plain_content": "Example WeChat Content"
        }

    async def crawl(self, url: str) -> Dict[str, Union[int, str, dict]]:
        result = {
            "status_code": 200,
            "error_message": "",
            "original_html": "",
            "plain_content": "",
            "title": "",
            "author": "",
            "publish_date": ""
        }

        html_content = await self.fetch_html(url)
        if not html_content:
            result["status_code"] = -1
            result["error_message"] = "Failed to fetch HTML"
            return result

        result["original_html"] = html_content
        domain = urlparse(url).netloc

        try:
            if domain in self.scraper_map:
                extracted_data = self.scraper_map[domain](html_content)
            else:
                extracted_data = self.extract_content(html_content, url)
            result.update(extracted_data)
        except Exception as e:
            result["status_code"] = -1
            result["error_message"] = f"Content extraction failed: {str(e)}"

        return result

    @classmethod
    async def create(cls):
        instance = cls()
        await instance.get_browser()  # 确保浏览器和页面已初始化
        return instance

    @classmethod
    async def cleanup(cls):
        if cls._instance:
            await cls._instance.close_browser()


# 创建实例
# crawler = await AsyncCrawler.create()
# 爬取 URL：
# result = await crawler.crawl("https://example.com")
# 清理资源：
# await AsyncCrawler.cleanup()