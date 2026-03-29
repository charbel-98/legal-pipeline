from __future__ import annotations

from legal_pipeline.application.use_cases.run_transform import run_transform, transform_record
from tests.fakes import FakeMetadataRepository, FakeObjectStorage


def test_transform_record_cleans_html_and_writes_processed_output() -> None:
    object_storage = FakeObjectStorage(
        {
            "landing-zone/workplace_relations/labour_court/2024-01-01/lcr22912.html": (
                b"<html><body><header>Nav</header><main><article><p>Decision body</p></article></main><footer>Foot</footer></body></html>"
            )
        }
    )

    processed_record = transform_record(
        landing_record=build_landing_record(),
        object_storage=object_storage,
        settings=FakeSettings(),
    )

    assert processed_record.content_type == "text/html"
    assert processed_record.file_name == "lcr22912.html"
    assert processed_record.path_to_file == (
        "processed-zone/workplace_relations/labour_court/2024-01-01/lcr22912.html"
    )
    assert processed_record.scrape_status == "transformed"
    payload = object_storage.uploads[0]["payload"].decode("utf-8")
    assert payload.startswith("<!DOCTYPE html>")
    assert '<meta charset="utf-8">' in payload
    assert "<main><article><p>Decision body</p></article></main>" in payload
    assert "<header>" not in payload
    assert "<footer>" not in payload


def test_transform_record_passes_pdf_through_unchanged() -> None:
    object_storage = FakeObjectStorage(
        {
            "landing-zone/workplace_relations/employment_appeals_tribunal/2013-01-01/ud181_11.pdf": (
                b"%PDF-1.7 fake payload"
            )
        }
    )

    processed_record = transform_record(
        landing_record=build_landing_record(
            body="Employment Appeals Tribunal",
            identifier="UD181_11",
            content_type="application/pdf",
            file_name="730e4ab5.pdf",
            path_to_file=(
                "landing-zone/workplace_relations/employment_appeals_tribunal/2013-01-01/ud181_11.pdf"
            ),
            link_to_doc="https://example.com/ud181_11.pdf",
        ),
        object_storage=object_storage,
        settings=FakeSettings(),
    )

    assert processed_record.content_type == "application/pdf"
    assert processed_record.file_name == "ud181_11.pdf"
    assert processed_record.path_to_file == (
        "processed-zone/workplace_relations/employment_appeals_tribunal/2013-01-01/ud181_11.pdf"
    )
    assert object_storage.uploads[0]["payload"] == b"%PDF-1.7 fake payload"


def test_run_transform_persists_processed_records() -> None:
    repository = FakeMetadataRepository(
        [
            build_landing_record(),
            build_landing_record(
                body="Employment Appeals Tribunal",
                identifier="UD181_11",
                content_type="application/pdf",
                file_name="730e4ab5.pdf",
                path_to_file=(
                    "landing-zone/workplace_relations/employment_appeals_tribunal/2013-01-01/ud181_11.pdf"
                ),
                link_to_doc="https://example.com/ud181_11.pdf",
            ),
        ]
    )
    object_storage = FakeObjectStorage(
        {
            "landing-zone/workplace_relations/labour_court/2024-01-01/lcr22912.html": (
                b"<html><body><main><p>Decision body</p></main></body></html>"
            ),
            "landing-zone/workplace_relations/employment_appeals_tribunal/2013-01-01/ud181_11.pdf": (
                b"%PDF-1.7 fake payload"
            ),
        }
    )

    run_transform(
        start_date="2013-01-01",
        end_date="2024-01-31",
        metadata_repository=repository,
        object_storage=object_storage,
        settings=FakeSettings(),
    )

    assert len(repository.processed_records) == 2
    html_record = repository.processed_records["workplace_relations:Labour Court:LCR22912"]
    pdf_record = repository.processed_records[
        "workplace_relations:Employment Appeals Tribunal:UD181_11"
    ]
    assert html_record["path_to_file"].startswith("processed-zone/")
    assert html_record["scrape_status"] == "transformed"
    assert pdf_record["content_type"] == "application/pdf"
    assert pdf_record["file_name"] == "ud181_11.pdf"


def build_landing_record(
    body: str = "Labour Court",
    identifier: str = "LCR22912",
    content_type: str = "text/html",
    file_name: str = "lcr22912.html",
    path_to_file: str = "landing-zone/workplace_relations/labour_court/2024-01-01/lcr22912.html",
    link_to_doc: str = "https://example.com/lcr22912.html",
) -> dict[str, object]:
    return {
        "source": "workplace_relations",
        "body": body,
        "identifier": identifier,
        "title": identifier,
        "description": "Example description",
        "case_number": "CD/24/11",
        "record_date": "2024-01-23",
        "partition_date": "2024-01-01" if body == "Labour Court" else "2013-01-01",
        "source_page_url": "https://example.com/search",
        "link_to_doc": link_to_doc,
        "file_name": file_name,
        "content_type": content_type,
        "path_to_file": path_to_file,
        "file_hash": "existing-hash",
        "scrape_status": "stored",
    }


class FakeSettings:
    minio_processed_bucket = "processed-zone"
