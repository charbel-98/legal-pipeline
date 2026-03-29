from enum import StrEnum


class ScrapeStatus(StrEnum):
    PENDING = "pending"
    SCRAPED = "scraped"
    STORED = "stored"
    UNCHANGED = "unchanged"
    TRANSFORMED = "transformed"
