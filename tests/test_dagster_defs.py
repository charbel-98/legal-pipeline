from legal_pipeline.infrastructure.orchestration import dagster_defs


def test_build_run_config_reuses_same_filters_for_ingest_and_transform() -> None:
    run_config = dagster_defs.build_run_config(
        start_date="2024-01-01",
        end_date="2024-01-31",
        body="Labour Court",
        topic="Dismissal",
    )

    assert run_config == {
        "ops": {
            "ingest_op": {
                "config": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31",
                    "body": "Labour Court",
                    "case_number": None,
                    "decision_number": None,
                    "legislation": None,
                    "topic": "Dismissal",
                    "keyword": None,
                }
            },
            "transform_op": {
                "config": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31",
                    "body": "Labour Court",
                    "case_number": None,
                    "decision_number": None,
                    "legislation": None,
                    "topic": "Dismissal",
                    "keyword": None,
                }
            },
        }
    }


def test_legal_pipeline_job_runs_scrape_then_transform(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, str | None]]] = []

    def fake_run_scrape(
        start_date: str,
        end_date: str,
        body: str | None = None,
        case_number: str | None = None,
        decision_number: str | None = None,
        legislation: str | None = None,
        topic: str | None = None,
        keyword: str | None = None,
    ) -> None:
        calls.append(
            (
                "scrape",
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "body": body,
                    "case_number": case_number,
                    "decision_number": decision_number,
                    "legislation": legislation,
                    "topic": topic,
                    "keyword": keyword,
                },
            )
        )

    def fake_run_transform(start_date: str, end_date: str) -> None:
        calls.append(
            (
                "transform",
                {
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
        )

    monkeypatch.setattr(dagster_defs, "run_scrape", fake_run_scrape)
    monkeypatch.setattr(dagster_defs, "run_transform", fake_run_transform)

    result = dagster_defs.execute_legal_pipeline_job(
        start_date="2024-01-01",
        end_date="2024-01-31",
        body="Labour Court",
    )

    assert result.success is True
    assert calls == [
        (
            "scrape",
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "body": "Labour Court",
                "case_number": None,
                "decision_number": None,
                "legislation": None,
                "topic": None,
                "keyword": None,
            },
        ),
        (
            "transform",
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        ),
    ]
