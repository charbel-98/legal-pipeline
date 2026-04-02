import scrapy
from legal_cases_scraper.items import LegalCaseItem

class LegalCasesSpiderSpider(scrapy.Spider):
    name = "legal_cases_spider"
    allowed_domains = ["www.workplacerelations.ie"]
    start_urls = ["https://www.workplacerelations.ie/en/search/?advance=true"]

    def parse(self, response):
        yield scrapy.FormRequest.from_response(
            response,
            formid="form",
            formdata={
                # keyword box; leave empty if you only want filters
                "ctl00$ContentPlaceHolder_Main$TextBox1": "",
                # Start Date / Finish Date
                "ctl00$ContentPlaceHolder_Main$TextBox2": "01/01/2024",
                "ctl00$ContentPlaceHolder_Main$TextBox3": "31/01/2024",
                # Body = Workplace Relations Commission
                "ctl00$ContentPlaceHolder_Main$CB2$CB2_3": "15376",
                # submit button
                "ctl00$ContentPlaceHolder_Main$refine_btn": "",
            },
            callback=self.parse_results,
        )

    def parse_results(self, response: scrapy.http.Response):
        cases = response.css('.item-list li.each-item')
        for case in cases:
            item = LegalCaseItem()
            item['identifier'] = case.css('h2.title').attrib['title']
            item['title'] = case.css('h2.title').attrib['title']
            item['url'] = case.css('h2.title a::attr(href)').get()
            item['date'] = case.css('span.date::text').get()
            item['description'] = case.css('p.description::text').get()
            
            # we go to the details page
            full_url = response.urljoin(item['url'])
            yield scrapy.Request(url=full_url, callback=self.parse_details, meta={'item': item})
        
    def parse_details(self, response: scrapy.http.Response):
        item = response.meta['item']
        
        # this html page should be extracted and saved to a file
        with open(f"{item['identifier']}.html", "w") as f:
            f.write(response.text)
        yield item
        
