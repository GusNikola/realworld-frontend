"""Browser smoke test for the built frontend image.

Usage: smoke.py FRONTEND_URL API_URL

Loads the home page in Chromium with the API mocked, so no backend is needed, and
checks that the article list renders and that every API request goes to API_URL.
A wrong host or port baked into the bundle fails the test instead of leaving the
page loading forever in production.
"""

import json
import sys
from urllib.parse import urlsplit

ARTICLE_TITLE = "E2E smoke article"
API_TYPES = {"fetch", "xhr"}

_AUTHOR = {"username": "e2e", "bio": "", "image": None, "following": False}
_ARTICLE = {
    "slug": "e2e-smoke-article",
    "title": ARTICLE_TITLE,
    "description": "Rendered from a mocked API response",
    "body": "Body",
    "tagList": ["e2e"],
    "createdAt": "2026-01-01T00:00:00.000Z",
    "updatedAt": "2026-01-01T00:00:00.000Z",
    "favorited": False,
    "favoritesCount": 0,
    "author": _AUTHOR,
}
FIXTURES = {
    "/tags": {"tags": ["e2e"]},
    "/articles": {"articles": [_ARTICLE], "articlesCount": 1},
}


def _origin(url: str) -> tuple[str, str, int | None]:
    parts = urlsplit(url)
    default = {"http": 80, "https": 443}.get(parts.scheme)
    return parts.scheme, parts.hostname or "", parts.port or default


def _under(url: str, base: str) -> bool:
    if _origin(url) != _origin(base):
        return False
    base_path = urlsplit(base).path.rstrip("/")
    path = urlsplit(url).path
    return path == base_path or path.startswith(base_path + "/")


def classify(url: str, resource_type: str, frontend_url: str, api_url: str) -> str:
    if resource_type in API_TYPES:
        return "api" if _under(url, api_url) else "unexpected-api"
    return "frontend" if _under(url, frontend_url) else "external"


def fixture_for(path: str) -> dict | None:
    return FIXTURES.get(path.removeprefix("/api"))


def main(argv: list[str]) -> int:
    from playwright.sync_api import sync_playwright

    frontend_url, api_url = argv
    api_path = urlsplit(api_url).path.rstrip("/")
    unexpected: list[str] = []
    missing: list[str] = []

    def handle(route, request) -> None:
        kind = classify(request.url, request.resource_type, frontend_url, api_url)
        if kind == "api":
            path = urlsplit(request.url).path
            body = fixture_for("/api" + path.removeprefix(api_path))
            if body is None:
                missing.append(request.url)
                route.fulfill(status=404, json={"errors": {"body": ["not mocked"]}})
            else:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
        elif kind == "frontend":
            route.continue_()
        else:
            if kind == "unexpected-api":
                unexpected.append(request.url)
            route.abort()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route("**/*", handle)
        page.goto(frontend_url)
        try:
            page.get_by_text(ARTICLE_TITLE).wait_for(timeout=15_000)
            rendered = True
        except Exception:
            rendered = False
        browser.close()

    for url in unexpected:
        print(f"FAIL: API request outside {api_url}: {url}")
    for url in missing:
        print(f"note: no fixture for {url}")
    if not rendered:
        print("FAIL: the article list did not render")
    if rendered and not unexpected:
        print("Smoke test passed: home page rendered from the API at", api_url)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
