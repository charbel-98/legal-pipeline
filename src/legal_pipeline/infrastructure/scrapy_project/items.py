import scrapy


class WorkplaceRelationsItem(scrapy.Item):
    source = scrapy.Field()
    body = scrapy.Field()
    identifier = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    case_number = scrapy.Field()
    record_date = scrapy.Field()
    partition_date = scrapy.Field()
    source_page_url = scrapy.Field()
    document_url = scrapy.Field()
    file_name = scrapy.Field()
    content_type = scrapy.Field()
    content_bytes = scrapy.Field()
    content_html = scrapy.Field()
    storage_path = scrapy.Field()
    file_hash = scrapy.Field()
    scrape_status = scrapy.Field()
