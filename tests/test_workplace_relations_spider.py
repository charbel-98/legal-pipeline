import pytest

scrapy = pytest.importorskip("scrapy")
from scrapy.http import HtmlResponse, Request, Response

from legal_pipeline.infrastructure.scrapy_project.spiders.workplace_relations_spider import (
    _extract_detail_metadata,
    _extract_attachment_href,
    _has_meaningful_html_content,
    _resolve_identifier,
    _is_download_response,
)


def test_has_meaningful_html_content_prefers_real_decision_body() -> None:
    response = _build_html_response(
        """
        <html>
          <body>
            <div class="content">
              <p>FULL DECISION</p>
              <p>This is a substantial decision body with enough text to clearly represent
              a parsed legal decision rather than a shell page or navigation fragment.</p>
            </div>
            <footer><a href="/en/privacy-policy/cookie-policy.pdf">Cookie policy</a></footer>
          </body>
        </html>
        """
    )

    assert _has_meaningful_html_content(response) is True
    assert _extract_attachment_href(response) is None


def test_extract_attachment_href_ignores_footer_links_outside_content() -> None:
    response = _build_html_response(
        """
        <html>
          <body>
            <div class="shell"><p>Minimal shell page</p></div>
            <footer><a href="/en/privacy-policy/cookie-policy.pdf">Cookie policy</a></footer>
          </body>
        </html>
        """
    )

    assert _has_meaningful_html_content(response) is False
    assert _extract_attachment_href(response) is None


def test_extract_attachment_href_reads_related_file_downloads() -> None:
    response = _build_html_response(
        """
        <html>
          <body>
            <h1 class="page-title">UD181/11</h1>
            <div class="content"></div>
            <div class="related-items related-file">
              <div class="related-item-content">
                <p class="name">730e4ab5-ce82-4114-abd1-29e805b660ee</p>
                <p class="file-info"><span class="extension">PDF</span></p>
                <a class="download" href="/en/eat_import/2013/01/730e4ab5-ce82-4114-abd1-29e805b660ee.pdf">Download</a>
              </div>
            </div>
          </body>
        </html>
        """
    )

    assert _has_meaningful_html_content(response) is False
    assert _extract_attachment_href(response) == "/en/eat_import/2013/01/730e4ab5-ce82-4114-abd1-29e805b660ee.pdf"


def test_is_download_response_detects_pdf_by_header() -> None:
    response = HtmlResponse(
        url="https://example.com/documents/case-report",
        request=Request("https://example.com/documents/case-report"),
        body=b"%PDF-1.7 fake payload",
        encoding="utf-8",
    )
    response.headers[b"Content-Type"] = b"application/pdf"

    assert _is_download_response(response) is True


def test_resolve_identifier_prefers_url_slug_for_numeric_eat_refs() -> None:
    assert (
        _resolve_identifier(
            raw_identifier="47535",
            detail_path="/en/cases/2013/january/pw169_2011.html",
            title="PW169/2011",
        )
        == "PW169_2011"
    )


def test_extract_detail_metadata_enriches_related_file_pages() -> None:
    response = _build_html_response(
        """
        <html>
          <body>
            <h1 class="page-title">UD181/11</h1>
            <div class="content"></div>
            <div class="related-items related-file">
              <div class="related-item-content">
                <p class="name">730e4ab5-ce82-4114-abd1-29e805b660ee</p>
                <p class="file-info"><span class="extension">PDF</span> | <span class="size">5KB</span></p>
                <a class="download" href="/en/eat_import/2013/01/730e4ab5-ce82-4114-abd1-29e805b660ee.pdf">Download</a>
              </div>
            </div>
          </body>
        </html>
        """
    )

    detail = _extract_detail_metadata(
        response,
        {
            "identifier": "UD181_11",
            "title": "UD181/11",
            "description": None,
            "record_date": "2013-01-30",
            "file_name": None,
        },
    )

    assert detail["title"] == "UD181/11"
    assert detail["record_date"] == "2013-01-30"
    assert detail["file_name"] == "730e4ab5-ce82-4114-abd1-29e805b660ee.pdf"


def test_extract_detail_metadata_uses_partial_item_for_binary_response() -> None:
    response = Response(
        url="https://www.workplacerelations.ie/en/eat_import/2013/01/730e4ab5-ce82-4114-abd1-29e805b660ee.pdf",
        request=Request("https://www.workplacerelations.ie/en/eat_import/2013/01/730e4ab5-ce82-4114-abd1-29e805b660ee.pdf"),
    )

    detail = _extract_detail_metadata(
        response,
        {
            "identifier": "UD181_11",
            "title": "UD181/11",
            "description": None,
            "record_date": "2013-01-30",
            "file_name": "730e4ab5-ce82-4114-abd1-29e805b660ee.pdf",
        },
    )

    assert detail["title"] == "UD181/11"
    assert detail["record_date"] == "2013-01-30"
    assert detail["content_html"] is None
    assert detail["file_name"] == "730e4ab5-ce82-4114-abd1-29e805b660ee.pdf"


def _build_html_response(body: str) -> HtmlResponse:
    return HtmlResponse(
        url="https://www.workplacerelations.ie/en/cases/2024/january/example.html",
        request=Request("https://www.workplacerelations.ie/en/cases/2024/january/example.html"),
        body=body.encode("utf-8"),
        encoding="utf-8",
    )
