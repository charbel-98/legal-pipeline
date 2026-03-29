from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from legal_pipeline.interfaces.cli.main import app

runner = CliRunner()


def _fake_settings(**overrides):
    defaults = {
        "default_start_date": "2024-01-01",
        "default_end_date": "2024-01-31",
        "json_logs": False,
        "log_level": "WARNING",
        "artifacts_dir": "artifacts/scrape",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_scrape_uses_default_dates_when_none_provided() -> None:
    settings = _fake_settings()
    with (
        patch("legal_pipeline.interfaces.cli.main.get_settings", return_value=settings),
        patch("legal_pipeline.application.logging.logger.configure_logging"),
        patch("legal_pipeline.interfaces.cli.main.run_scrape") as mock_run_scrape,
    ):
        result = runner.invoke(app, ["scrape"])

    assert result.exit_code == 0
    mock_run_scrape.assert_called_once()
    call_args = mock_run_scrape.call_args
    assert call_args.args[0] == "2024-01-01"
    assert call_args.args[1] == "2024-01-31"


def test_scrape_passes_explicit_dates_through() -> None:
    settings = _fake_settings()
    with (
        patch("legal_pipeline.interfaces.cli.main.get_settings", return_value=settings),
        patch("legal_pipeline.application.logging.logger.configure_logging"),
        patch("legal_pipeline.interfaces.cli.main.run_scrape") as mock_run_scrape,
    ):
        result = runner.invoke(app, ["scrape", "--start-date", "2023-06-01", "--end-date", "2023-06-30"])

    assert result.exit_code == 0
    call_args = mock_run_scrape.call_args
    assert call_args.args[0] == "2023-06-01"
    assert call_args.args[1] == "2023-06-30"


def test_orchestrate_exits_with_code_1_on_failure() -> None:
    settings = _fake_settings()
    failed_result = MagicMock()
    failed_result.success = False
    with (
        patch("legal_pipeline.interfaces.cli.main.get_settings", return_value=settings),
        patch("legal_pipeline.application.logging.logger.configure_logging"),
        patch(
            "legal_pipeline.interfaces.cli.main.execute_legal_pipeline_job",
            return_value=failed_result,
        ),
    ):
        result = runner.invoke(app, ["orchestrate", "--start-date", "2024-01-01", "--end-date", "2024-01-31"])

    assert result.exit_code == 1


def test_orchestrate_exits_with_code_0_on_success() -> None:
    settings = _fake_settings()
    success_result = MagicMock()
    success_result.success = True
    with (
        patch("legal_pipeline.interfaces.cli.main.get_settings", return_value=settings),
        patch("legal_pipeline.application.logging.logger.configure_logging"),
        patch(
            "legal_pipeline.interfaces.cli.main.execute_legal_pipeline_job",
            return_value=success_result,
        ),
    ):
        result = runner.invoke(app, ["orchestrate", "--start-date", "2024-01-01", "--end-date", "2024-01-31"])

    assert result.exit_code == 0
