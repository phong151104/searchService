import asyncio
from crawl4ai import *
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.browser_manager import BrowserManager
from datetime import datetime
import re

import utils
from config import Config


# Fix error: playwright._impl._errors.TargetClosedError: BrowserType.launch: Target page, context or browser
async def patched_async_playwright__crawler_strategy_close(self) -> None:
    """
    Close the browser and clean up resources.

    This patch addresses an issue with Playwright instance cleanup where the static instance
    wasn't being properly reset, leading to issues with multiple crawls.

    Issue: https://github.com/unclecode/crawl4ai/issues/842

    Returns:
        None
    """
    await self.browser_manager.close()
    # Reset the static Playwright instance
    BrowserManager._playwright_instance = None


AsyncPlaywrightCrawlerStrategy.close = patched_async_playwright__crawler_strategy_close


def extract_date_from_url(url):
    """Extract date from URL patterns like /2024/03/21/ or /2024-03-21/"""
    date_patterns = [
        r'/(\d{4})/(\d{2})/(\d{2})/',  # /2024/03/21/
        r'/(\d{4})-(\d{2})-(\d{2})/',  # /2024-03-21/
        r'/(\d{2})-(\d{2})-(\d{4})/',  # /21-03-2024/
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, url)
        if match:
            try:
                if len(match.groups()) == 3:
                    if pattern == r'/(\d{2})-(\d{2})-(\d{4})/':
                        day, month, year = match.groups()
                    else:
                        year, month, day = match.groups()
                    return datetime(int(year), int(month), int(day))
            except ValueError:
                continue
    return None

def filter_links_by_date(urls, start_date=None, end_date=None):
    """Filter URLs based on date range"""
    if not start_date and not end_date:
        return urls
        
    filtered_urls = []
    for url in urls:
        date = extract_date_from_url(url)
        if date:
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue
        filtered_urls.append(url)
    return filtered_urls


async def crawl4ai_arun_many(urls, start_date=None, end_date=None):
    # Filter URLs by date if date range is provided
    if start_date or end_date:
        urls = filter_links_by_date(urls, start_date, end_date)
    
    run_config = CrawlerRunConfig(
        word_count_threshold=10,
        excluded_tags=["nav", "footer", "header", "img"],
        exclude_external_links=True,
        # Media filtering
        exclude_external_images=True,
        exclude_internal_links=False,  # Allow internal links
        exclude_social_media_links=True,
        excluded_selector=Config.EXCLUDED_CSS_SELECTOR,
        stream=False,
        cache_mode=CacheMode.BYPASS,
        page_timeout=Config.CRAWL4AI_PAGE_TIMEOUT,
        only_text=True,
        remove_forms=True,
        remove_overlay_elements=True,
        max_depth=3,
        max_pages_per_domain=20
    )
    
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=90.0,
        check_interval=1.0,
        max_session_permit=10,
        monitor=None
    )
    
    results = {}
    async with AsyncWebCrawler() as crawler:
        crawl_results = await crawler.arun_many(urls=urls,
                                                config=run_config,
                                                dispatcher=dispatcher
                                                )
        for r in crawl_results:
            if r.success:
                results[r.url] = r.markdown
            else:
                results[r.url] = None
        return results


def multiple_crawler(top_results):
    list_urls = [r['link'] for r in top_results]
    
    return_dict = asyncio.run(crawl4ai_arun_many(list_urls))
    
    for url, html in return_dict.items():
        for idx, result in enumerate(top_results):
            if result['link'] == url:
                if html:
                    short_text = str(html).strip()
                    # short_text = str(html).strip()[:4000]
                else:
                    short_text = ""
                
                if short_text:
                    top_results[idx]["content"] = short_text
                else:
                    top_results[idx]["content"] = None


def process_priority_domain(top_results, topk: int):
    priority_results = utils.get_valid_priority_domains(top_results=top_results)
    if priority_results:
        top_results = priority_results
    top_results = top_results[:topk]
    return top_results


def split_results(top_results):
    new_top_results = []
    priority_results = []
    
    for r in top_results:
        if utils.extract_domain(r['link']) in Config.MOST_PRIORITY_LINKS:
            priority_results.append(r)
        else:
            new_top_results.append(r)
    priority_results = priority_results[:1]
    return new_top_results, priority_results