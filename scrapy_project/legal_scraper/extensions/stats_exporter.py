"""Scrapy extension — writes spider stats to a JSON file on close.

Activated when STATS_EXPORT_FILE is set in Scrapy settings (or via -s).
Used by the ingestion service to surface Scrapy stats back to Dagster.
"""

from __future__ import annotations

import json

from scrapy import signals
from scrapy.exceptions import NotConfigured


class StatsExporterExtension:
    def __init__(self, export_path: str) -> None:
        self._export_path = export_path

    @classmethod
    def from_crawler(cls, crawler):
        path = crawler.settings.get("STATS_EXPORT_FILE")
        if not path:
            raise NotConfigured
        ext = cls(export_path=path)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_closed(self, spider, reason):
        stats = spider.crawler.stats.get_stats()
        serialisable = {}
        for key, value in stats.items():
            try:
                json.dumps(value)
                serialisable[key] = value
            except (TypeError, ValueError):
                serialisable[key] = str(value)

        with open(self._export_path, "w", encoding="utf-8") as fh:
            json.dump(serialisable, fh)
