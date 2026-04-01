import scrapy


class LegalCasesSpiderSpider(scrapy.Spider):
    name = "legal_cases_spider"
    allowed_domains = ["www.workplacerelations.ie"]
    start_urls = ["https://www.workplacerelations.ie/en/search/?advance=true"]

    def parse(self, response):
        pass
