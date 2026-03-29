import pytest

scrapy = pytest.importorskip("scrapy")
from scrapy.http import HtmlResponse, Request

from legal_pipeline.infrastructure.scrapy_project.spiders.workplace_relations_spider import (
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


def _build_html_response(body: str) -> HtmlResponse:
    return HtmlResponse(
        url="https://www.workplacerelations.ie/en/cases/2024/january/example.html",
        request=Request("https://www.workplacerelations.ie/en/cases/2024/january/example.html"),
        body=body.encode("utf-8"),
        encoding="utf-8",
    )
