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
import logging


class GeneralCrawler:
    def __init__(self, restart_threshold=1000):
        # 特定域名的处理器映射，可以根据需要扩展
        self.scraper_map = {
            "mp.weixin.qq.com": self.wechat_handler
            # TODO: 可以添加更多特定域处理器
        }

        # 定义使用动态JS技术的域名，在名单中的网页会用pyppeteer获取渲染后的HTML
        self.ajax_domains = [
            "36kr.com"
            # TODO: 可以添加更多动态JS技术的域名            
        ]

        self.browser = None
        atexit.register(self.atexit_close_browser)

        # 定义使用pyppeteer打开页面数量
        self.page_count = 0
        self.restart_threshold = restart_threshold

    async def init_browser(self):
        # 当大于restart_threshold阈值则重启浏览器
        if not self.browser or self.page_count >= self.restart_threshold:
            if self.browser:
                await self.close_browser()
            self.browser = await launch(headless=True)
            self.page_count = 0
            logging.info("New browser instance created")

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
            logging.info("Browser instance closed")

    def atexit_close_browser(self):
        if self.browser:
            asyncio.get_event_loop().run_until_complete(self.close_browser())

    async def fetch_with_pyppeteer(self, url: str) -> Union[str, None]:
        '''
        使用pyppeteer获取HTML
        '''
        await self.init_browser()
        page = None
        try:
            page = await self.browser.newPage()
            self.page_count += 1
            await page.goto(url, waitUntil='networkidle0')
            content = await page.content()
            logging.info(f"Successfully fetched HTML content from {url} using pyppeteer (Page count: {self.page_count})")
            return content
        except Exception as exc:
            logging.error(f"Pyppeteer error: {exc}")
            return None
        finally:
            # 确保页面关闭不再占用资源
            if page:
                await page.close()

    async def fetch_html_async(self, url: str) -> Union[str, None]:
        '''
         获取HTML的主函数：
         如果域名在JS动态网页名单里，则会使用pyppeteer来获取渲染后的HTML，否则试用HTTPX获取
        '''
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        result = None

        if domain in self.ajax_domains:
            # 使用pyppeteer来获取渲染后的HTML
            result = await self.fetch_with_pyppeteer(url)
            return result
        else:
            # 使用 httpx 的异步客户端
            async with httpx.AsyncClient() as client:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/604.1 Edg/112.0.100.0'}
                    response = await client.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    logging.info(f"Successfully fetched HTML content from {url} using httpx")
                    result = response.text
                    return result
                except httpx.RequestError as exc:
                    logging.error(f"HTTP request error: {exc}")
                    return result
                except httpx.HTTPStatusError as exc:
                    logging.error(f"HTTP status error: {exc}")
                    return result

    async def extract_content(self, html_content: str, url: str) -> Dict[str, str]:
        """使用GeneralNewsExtractor和Trafilatura提取网页内容"""
        result = {
            "title": "",
            "author": "",
            "publish_date": "",
            "content": html_content,
            "plain_content": ""
        }
        try:
            # 首先使用GeneralNewsExtractor
            extractor = GeneralNewsExtractor()
            gne_result = extractor.extract(html_content, noise_node_list=['//div[@class="comment-list"]'])
            result['title'] = gne_result.get('title', '')
            result['author'] = gne_result.get('author', '')
            result['publish_date'] = gne_result.get('publish_time', '')
            result['plain_content'] = gne_result.get('content', '')

            # 如果GNE提取失败，使用Trafilatura
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

            if result['plain_content']:
                logging.info("内容提取成功")
            else:
                logging.warning("内容提取失败")

        except Exception as exc:
            logging.error(f"Content extraction error: {exc}")
        
        return result

    def wechat_handler(self, html_content: str) -> Dict[str, str]:
        """特定域名的处理器示例"""
        # TODO: 针对mp.weixin.qq.com的自定义处理逻辑
        logging.info("Using specific handler for mp.weixin.qq.com")
        return {"title": "Example Title", "author": "Example Author", "publish_date": "2024-07-25", "plain_content": "Example Content"}

    def llm_fallback(self, html_content: str, url: str) -> Dict[str, str]:
        """LLM兜底处理逻辑"""
        logging.info("Using LLM fallback for content extraction")
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
            result["error_message"] = "Failed to fetch HTML content"
            return result

        result["original_html"] = html_content

        # 确定域名并检查是否有特定的处理器
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        if domain == "mp.weixin.qq.com":
            extracted_data = self.wechat_handler(html_content)
        else:
            extracted_data = await self.extract_content(html_content, url)

        # 如果提取失败，使用LLM兜底
        if not extracted_data['plain_content']:
            result["error_message"] += " Content extraction failed. Using LLM fallback."
            extracted_data = self.llm_fallback(html_content, url)

        result.update(extracted_data)
        return result
