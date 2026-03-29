from bs4 import BeautifulSoup


def extract_relevant_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for selector in ["nav", "header", "footer", "script", "style"]:
        for node in soup.select(selector):
            node.decompose()

    content = soup.find("main")
    if content is None:
        content = soup.find("article")

    if content is None:
        body = soup.find("body")
        content = body if body is not None else soup

    return (
        "<!DOCTYPE html>"
        '<html lang="en"><head><meta charset="utf-8"></head><body>'
        f"{content!s}"
        "</body></html>"
    )
