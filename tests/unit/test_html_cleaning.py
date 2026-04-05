from app.services.html_cleaning_service import clean_html


def test_strips_nav_and_footer():
    raw = b"<html><body><nav>Menu</nav><main>Case content</main><footer>Footer</footer></body></html>"
    cleaned = clean_html(raw).decode()
    assert "Menu" not in cleaned
    assert "Footer" not in cleaned
    assert "Case content" in cleaned


def test_strips_script_tags():
    raw = b"<html><body><script>alert(1)</script><main>Content</main></body></html>"
    cleaned = clean_html(raw).decode()
    assert "alert" not in cleaned


def test_extracts_main_content_node():
    raw = b"<html><body><div class='content'><p>Case text</p></div></body></html>"
    cleaned = clean_html(raw).decode()
    assert "Case text" in cleaned


def test_empty_body_does_not_raise():
    clean_html(b"<html><body></body></html>")
