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
            item['title'] = case.css('h2.title').attrib['title']
            item['identifier'] = case.css('h2.title').attrib['title']
            item['description'] = case.css('p.description::text').get()
            item['source'] = "Workplace Relations Commission"
            item['body'] = "TODO LATER"
            item['case_number'] = "TODO LATER"
            item['record_date'] = case.css('span.date::text').get()
            item['partition_date'] = "TODO LATER"
            item['source_page_url'] = case.css('h2.title a::attr(href)').get()
            
            # we go to the details page
            full_url = response.urljoin(item['source_page_url'])
            yield scrapy.Request(url=full_url, callback=self.parse_document_resource, meta={'item': item})
        
    def parse_document_resource(self, response: scrapy.http.Response):
        item = response.meta['item']
        # we should detect whether the page is and html page or it has a pdf link, we should pass the content to the pipeline

        if self._is_download_response(response):
            yield self._build_file_item(response, item)
            return

        if self._has_meaningful_html_content(response):
            yield self._build_html_item(response, item)
            return

        attachment_href = _extract_attachment_href(response)
        if attachment_href:
            attachment_url = response.urljoin(attachment_href)
            yield response.follow(attachment_url, callback=self.parse_document_resource, meta={'item': item})
            return
        
        yield self._build_html_item(response, item)

    def _extract_attachment_href(response: Any) -> str | None:
        selectors = [
            "div.content a[href$='.pdf']::attr(href)",
            "div.content a[href$='.doc']::attr(href)",
            "div.content a[href$='.docx']::attr(href)",
            "div.related-items.related-file a.download::attr(href)",
            "div.related-item-content a.download::attr(href)",
        ]
        for selector in selectors:
            href = response.css(selector).get()
            if href:
                return href
        xpath_selectors = [
            "//div[contains(@class, 'content')]//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'full case report')]/@href",
            "//div[contains(@class, 'content')]//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view')][contains(@href, '.pdf') or contains(@href, '.doc')]/@href",
        ]
        for selector in xpath_selectors:
            href = response.xpath(selector).get()
            if href:
                return href
        return None
    
    def _build_html_item(
        self, response: Any, partial_item: dict[str, Any]
    ) -> LegalCaseItem:
        detail_metadata = _extract_detail_metadata(response, partial_item)
        item = self._build_base_item(response, partial_item, detail_metadata)
        item["content_type"] = (
            _normalize_content_type(response.headers.get("Content-Type")) or "text/html"
        )
        item["content_bytes"] = None
        item["content_html"] = detail_metadata["content_html"]

        
        return item
    
    def _build_file_item(
        self, response: Any, partial_item: dict[str, Any]
    ) -> LegalCaseItem:
        detail_metadata = _extract_detail_metadata(response, partial_item)
        item = self._build_base_item(response, partial_item, detail_metadata)
        item["link_to_doc"] = response.url
        item["content_type"] = (
            _normalize_content_type(response.headers.get("Content-Type"))
            or "application/octet-stream"
        )
        item["content_bytes"] = response.body
        item["content_html"] = None

        return item

    def _is_download_response(response: Any) -> bool:
        content_type = _normalize_content_type(response.headers.get("Content-Type"))
        if content_type in {
            "application/msword",
            "application/pdf",

        }:
            return True
        return False

    def _is_download_response(response: Any) -> bool:
        content_type = _normalize_content_type(response.headers.get("Content-Type"))
        if content_type in {
            "application/msword",
            "application/pdf",
            "application/vnd.ms-word.document.macroenabled.12",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            return True
        path = urlparse(response.url).path.lower()
        return path.endswith((".pdf", ".doc", ".docx"))

    def _has_meaningful_html_content(response: Any) -> bool:
        content_node = _extract_content_html(response)
        if not content_node:
            return False
        text_content = _clean_text(_extract_content_text(response))
        return bool(text_content and len(text_content) >= 100)

    def _extract_attachment_href(response: Any) -> str | None:
        selectors = [
            "div.content a[href$='.pdf']::attr(href)",
            "div.content a[href$='.doc']::attr(href)",
            "div.content a[href$='.docx']::attr(href)",
            "div.related-items.related-file a.download::attr(href)",
            "div.related-item-content a.download::attr(href)",
        ]
        for selector in selectors:
            href = response.css(selector).get()
            if href:
                return href
        xpath_selectors = [
            "//div[contains(@class, 'content')]//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'full case report')]/@href",
            "//div[contains(@class, 'content')]//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view')][contains(@href, '.pdf') or contains(@href, '.doc')]/@href",
        ]
        for selector in xpath_selectors:
            href = response.xpath(selector).get()
            if href:
                return href
        return None
        
