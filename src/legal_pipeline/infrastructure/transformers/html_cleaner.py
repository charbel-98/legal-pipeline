from bs4 import BeautifulSoup


def extract_relevant_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for selector in ["nav", "header", "footer", "script", "style"]:
        for node in soup.select(selector):
            node.decompose()

    main = soup.find("main")
    if main is not None:
        return str(main)

    article = soup.find("article")
    if article is not None:
        return str(article)

    body = soup.find("body")
    return str(body if body is not None else soup)
