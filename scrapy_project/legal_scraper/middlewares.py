# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import random

import requests as http_requests
from scrapy import signals


class ScrapeOpsHeadersMiddleware:
    def __init__(self, api_key, enabled):
        self.api_key = api_key
        self.enabled = enabled
        self.headers_list = []

    @classmethod
    def from_crawler(cls, crawler):
        api_key = crawler.settings.get("SCRAPEOPS_API_KEY", "")
        enabled = crawler.settings.getbool("SCRAPEOPS_HEADERS_ENABLED", True)
        mw = cls(api_key, enabled)
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        if not self.enabled or not self.api_key:
            return
        try:
            resp = http_requests.get(
                "https://headers.scrapeops.io/v1/browser-headers",
                params={"api_key": self.api_key, "num_results": "10"},
                timeout=10,
            )
            resp.raise_for_status()
            self.headers_list = resp.json().get("result", [])
            spider.logger.info("ScrapeOpsHeadersMiddleware: loaded %d header sets", len(self.headers_list))
        except Exception as e:
            spider.logger.warning("ScrapeOpsHeadersMiddleware: failed to fetch headers — %s", e)

    def process_request(self, request):
        if not self.enabled or not self.headers_list:
            return None
        headers = random.choice(self.headers_list)
        for key, value in headers.items():
            request.headers[key] = value
        return None


class ScrapeOpsProxyMiddleware:
    def __init__(self, api_key, enabled):
        self.api_key = api_key
        self.enabled = enabled

    @classmethod
    def from_crawler(cls, crawler):
        api_key = crawler.settings.get("SCRAPEOPS_API_KEY", "")
        enabled = crawler.settings.getbool("SCRAPEOPS_PROXY_ENABLED", False)
        return cls(api_key, enabled)

    def process_request(self, request):
        if not self.enabled or request.meta.get("scrapeops_proxy_applied"):
            return None
        # Pass the API key as a header instead of embedding it in the URL to
        # prevent the key from appearing in Scrapy logs and error reports.
        proxied_url = f"https://proxy.scrapeops.io/v1/?url={request.url}"
        request = request.replace(url=proxied_url)
        request.headers["X-ScrapeOps-API-Key"] = self.api_key
        request.meta["scrapeops_proxy_applied"] = True
        return request


