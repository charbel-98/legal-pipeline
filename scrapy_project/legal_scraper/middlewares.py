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
        proxied_url = f"https://proxy.scrapeops.io/v1/?api_key={self.api_key}&url={request.url}"
        request = request.replace(url=proxied_url)
        request.meta["scrapeops_proxy_applied"] = True
        return request


class LegalCasesSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        yield from result

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # matching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s", spider.name)


class LegalCasesDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s", spider.name)
