import asyncio
import atexit
from pyppeteer import launch
import httpx
import logging
from urllib.parse import urlparse
import trafilatura
from typing import Dict, Union
from trafilatura import extract
from gne import GeneralNewsExtractor
import json

class BrowserManager:
    _instance = None
    _browser = None
    _lock = asyncio.Lock()
    _page_count = 0
    _restart_threshold = 1000

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance.init_browser()
        return cls._instance

    async def init_browser(self):
        if self._browser is None or not self._browser.isConnected() or self._page_count >= self._restart_threshold:
            if self._browser:
                await self.close_browser()
            self._browser = await launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
                ignoreHTTPSErrors=True,
                handleSIGINT=False,
                handleSIGTERM=False,
                handleSIGHUP=False
            )
            self._page_count = 0
            logging.info("新浏览器实例创建完成")

    async def get_page(self):
        await self.init_browser()
        page = await self._browser.newPage()
        self._page_count += 1
        logging.debug(f"第{self._page_count}次创建新的Tab页")
        return page

    async def close_page(self, page):
        if page:
            logging.debug("关闭当前Tab页")
            await page.close()

    async def close_browser(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page_count = 0
            logging.debug("浏览器实例关闭")

    @classmethod
    def register_shutdown(cls):
        atexit.register(cls.shutdown)

    @classmethod
    def shutdown(cls):
        if cls._instance:
            asyncio.get_event_loop().run_until_complete(cls._instance.close_browser())

class GeneralCrawler:
    def __init__(self):
        self.browser_manager = None
        self.scraper_map = {
            "mp.weixin.qq.com": self.wechat_handler
            # TODO: 定义更多特定域爬虫处理器
        }
        self.ajax_domains = [
            "36kr.com"
            # TODO: 定义更多JS动态页面域
        ]

    async def init_browser_manager(self):
        self.browser_manager = await BrowserManager.get_instance()

    async def fetch_with_pyppeteer(self, url: str) -> Union[str, None]:
        if not self.browser_manager:
            await self.init_browser_manager()
        
        page = None
        try:
            page = await self.browser_manager.get_page()
            await page.goto(url, waitUntil='networkidle0')
            content = await page.content()
            logging.info(f"Pyppeteer：成功获取{url}的HTML内容")
            return content
        except Exception as exc:
            logging.error(f"Pyppeteer： 获取HTML异常，原因是{exc}")
            return None
        finally:
            if page:
                await self.browser_manager.close_page(page)

    async def fetch_html_async(self, url: str) -> Union[str, None]:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        if domain in self.ajax_domains:
            return await self.fetch_with_pyppeteer(url)
        else:
            async with httpx.AsyncClient() as client:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/604.1 Edg/112.0.100.0'}
                    response = await client.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    logging.info(f"Httpx：成功获取{url}的HTML内容")
                    return response.text
                except httpx.RequestError as exc:
                    logging.error(f"Httpx：Http请求失败，详情是 {exc}")
                    return None
                except httpx.HTTPStatusError as exc:
                    logging.error(f"Httpx：Http状态异常，详情是 {exc}")
                    return None

    async def extract_content(self, html_content: str, url: str) -> Dict[str, str]:
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
                logging.info("NewsExtractor：内容提取成功")
            else:
                logging.warning("NewsExtractor：内容提取失败，即将使用Trafilatura重试")

            if not result['plain_content']:
                downloaded = trafilatura.extract(html_content, url=url, output_format="json", with_metadata=True, include_comments=False, include_images=True)
                if downloaded:
                    trafilatura_result = json.loads(downloaded)
                    result['title'] = result['title'] or trafilatura_result.get('title', '')
                    result['author'] = result['author'] or trafilatura_result.get('author', '')
                    result['publish_date'] = result['publish_date'] or trafilatura_result.get('date', '')
                    result['plain_content'] = result['plain_content'] or trafilatura_result.get('text', '')
                    logging.info("Trafilatura：内容提取成功")
                else:
                    logging.warning("Trafilatura：内容提取失败")

        except Exception as exc:
            logging.error(f"Content extraction error: {exc}")
        
        return result

    def wechat_handler(self, html_content: str) -> Dict[str, str]:
        logging.info("使用专用爬虫处理域：mp.weixin.qq.com")
        return {"title": "Example Title", "author": "Example Author", "publish_date": "2024-07-25", "plain_content": "Example Content"}

    def llm_fallback(self, html_content: str, url: str) -> Dict[str, str]:
        logging.info("尝试使用大模型提取正文内容")
        return {
            "title": "Fallback Title",
            "author": "Fallback Author",
            "publish_date": "Fallback Date",
            "plain_content": "Fallback Content"
        }

    async def crawl_async(self, url: str) -> Dict[str, Union[int, str, dict]]:
        result = {
            "status_code": 200,
            "error_message": "",
            "original_html": "",
            "plain_content": "",
            "title": "",
            "author": "",
            "publish_date": ""
        }

        html_content = await self.fetch_html_async(url)
        if not html_content:
            result["status_code"] = -1
            result["error_message"] = "最终获取HTML页面失败"
            return result

        result["original_html"] = html_content

        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        if domain in self.scraper_map:
            extracted_data = self.scraper_map[domain](html_content)
        else:
            extracted_data = await self.extract_content(html_content, url)

        if not extracted_data['plain_content']:
            result["error_message"] += "正文提取失败，尝试使用大模型作为兜底方案提取正文"
            extracted_data = self.llm_fallback(html_content, url)

        result.update(extracted_data)
        return result

# 在应用启动时注册关闭函数
BrowserManager.register_shutdown()