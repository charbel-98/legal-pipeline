from legal_pipeline.application.logging.logger import get_logger


def run_transform(start_date: str, end_date: str) -> None:
    logger = get_logger(__name__)
    logger.info("transform_run_started", start_date=start_date, end_date=end_date)
    logger.info("transform_run_scaffold_only")

