import logging
import sys
from typing import Any

import structlog

from legal_pipeline.application.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
    ]

    if settings.json_logs:
        handler = logging.StreamHandler(sys.stdout)
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
    else:
        handler = _build_pretty_handler(log_level, shared_processors)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    for noisy_logger in (
        "pymongo",
        "pymongo.command",
        "urllib3",
        "urllib3.connectionpool",
        "minio",
        "asyncio",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    framework_level = log_level if log_level <= logging.DEBUG else logging.WARNING
    for framework_logger in (
        "scrapy",
        "twisted",
    ):
        logging.getLogger(framework_logger).setLevel(framework_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def _build_pretty_handler(
    log_level: int,
    shared_processors: list[structlog.types.Processor],
) -> logging.Handler:
    try:
        from rich.logging import RichHandler
    except ModuleNotFoundError:
        fallback = logging.StreamHandler(sys.stdout)
        fallback.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared_processors,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=True),
                ],
            )
        )
        fallback.setLevel(log_level)
        return fallback

    handler = RichHandler(
        show_time=True,
        show_level=False,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        omit_repeated_times=False,
        log_time_format="%H:%M:%S",
    )
    handler.setLevel(log_level)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                _rich_event_renderer,
            ],
        )
    )
    return handler


def _rich_event_renderer(_: Any, __: str, event_dict: structlog.types.EventDict) -> str:
    level = str(event_dict.pop("level", "info")).lower()
    logger_name = str(event_dict.pop("logger", "app"))
    timestamp = str(event_dict.pop("timestamp", ""))
    event = str(event_dict.pop("event", ""))

    if event == "scrape_run_finished":
        return _render_scrape_summary(event_dict, logger_name, timestamp)

    icon, color = _icon_and_color(level, event)
    title = _pretty_event_name(event)
    details = _format_detail_pairs(event_dict)

    parts = [f"[{color}]{icon}[/{color}] [bold]{title}[/bold]"]
    if details:
        parts.append(f"[dim]{details}[/dim]")
    if logger_name and logger_name not in {"__main__", "root"}:
        parts.append(f"[grey50]{logger_name}[/grey50]")
    if timestamp:
        parts.append(f"[grey62]{timestamp}[/grey62]")
    return "  ".join(parts)


def _icon_and_color(level: str, event: str) -> tuple[str, str]:
    event_map = {
        "scrape_run_started": ("▶", "cyan"),
        "search_plan_prepared": ("◦", "blue"),
        "search_results_loaded": ("⌕", "cyan"),
        "detail_page_scraped": ("↳", "blue"),
        "landing_pipeline_retry": ("↻", "yellow"),
        "landing_pipeline_failed": ("✖", "red"),
        "scrape_run_finished": ("✔", "green"),
    }
    if event in event_map:
        return event_map[event]
    level_map = {
        "debug": ("·", "bright_black"),
        "info": ("●", "cyan"),
        "warning": ("▲", "yellow"),
        "error": ("✖", "red"),
        "critical": ("✖", "bold red"),
    }
    return level_map.get(level, ("●", "cyan"))


def _pretty_event_name(event: str) -> str:
    labels = {
        "scrape_run_started": "Scrape Started",
        "search_plan_prepared": "Search Plan Ready",
        "search_results_loaded": "Results Loaded",
        "detail_page_scraped": "Detail Parsed",
        "landing_pipeline_retry": "Landing Retry",
        "landing_pipeline_failed": "Landing Failure",
        "scrape_run_finished": "Scrape Finished",
    }
    if event in labels:
        return labels[event]
    return event.replace("_", " ").title()


def _format_detail_pairs(event_dict: dict[str, Any]) -> str:
    interesting_order = [
        "start_date",
        "end_date",
        "partition_date",
        "partition_start",
        "partition_end",
        "filters",
        "pages_crawled",
        "items_scraped",
        "stored_count",
        "unchanged_count",
        "failed_count",
        "retry_count",
        "identifier",
        "body",
        "operation",
        "attempt",
        "max_attempts",
        "error",
    ]
    rendered: list[str] = []
    for key in interesting_order:
        if key in event_dict:
            rendered.append(f"{key}={event_dict.pop(key)}")
    for key, value in event_dict.items():
        rendered.append(f"{key}={value}")
    return "  ".join(rendered)


def _render_scrape_summary(
    event_dict: dict[str, Any],
    logger_name: str,
    timestamp: str,
) -> str:
    lines = [
        "[green]✔[/green] [bold green]Scrape Finished[/bold green]",
        (
            f"[bold]Range[/bold] {event_dict.pop('start_date', '?')} -> "
            f"{event_dict.pop('end_date', '?')}"
        ),
        f"[bold]Filters[/bold] {event_dict.pop('filters', {})}",
        (
            f"[bold]Pages[/bold] {event_dict.pop('pages_crawled', 0)}    "
            f"[bold]Items[/bold] {event_dict.pop('items_scraped', 0)}"
        ),
        (
            f"[bold green]Stored[/bold green] {event_dict.pop('stored_count', 0)}    "
            f"[bold blue]Unchanged[/bold blue] {event_dict.pop('unchanged_count', 0)}    "
            f"[bold red]Failed[/bold red] {event_dict.pop('failed_count', 0)}    "
            f"[bold yellow]Retries[/bold yellow] {event_dict.pop('retry_count', 0)}"
        ),
    ]
    if logger_name and logger_name not in {"__main__", "root"}:
        lines.append(f"[grey50]{logger_name}[/grey50]")
    if timestamp:
        lines.append(f"[grey62]{timestamp}[/grey62]")
    return "\n".join(lines)
