from smoke import classify, fixture_for

FRONTEND = "http://frontend"
API = "https://app.example.com/api"


def test_api_request_to_api_url() -> None:
    assert classify(f"{API}/tags", "fetch", FRONTEND, API) == "api"


def test_api_request_with_wrong_port_is_unexpected() -> None:
    url = "https://app.example.com:3000/api/tags"

    assert classify(url, "fetch", FRONTEND, API) == "unexpected-api"


def test_api_request_to_other_host_is_unexpected() -> None:
    assert classify("http://localhost:3000/api/tags", "xhr", FRONTEND, API) == "unexpected-api"


def test_frontend_asset() -> None:
    assert classify(f"{FRONTEND}/main.js", "script", FRONTEND, API) == "frontend"


def test_external_image() -> None:
    url = "https://api.realworld.io/images/smiley.jpeg"

    assert classify(url, "image", FRONTEND, API) == "external"


def test_url_prefix_is_not_enough() -> None:
    # https://app.example.com/apix must not count as the API.
    assert classify("https://app.example.com/apix/tags", "fetch", FRONTEND, API) == "unexpected-api"


def test_fixture_for_tags() -> None:
    assert fixture_for("/api/tags") == {"tags": ["e2e"]}


def test_fixture_for_articles_contains_smoke_article() -> None:
    body = fixture_for("/api/articles")

    assert body["articlesCount"] == 1
    assert body["articles"][0]["title"] == "E2E smoke article"


def test_unknown_path_has_no_fixture() -> None:
    assert fixture_for("/api/user") is None
