import gzip
import json
from pathlib import Path

from bundle_size import Limits, evaluate, main, measure


def write_asset(directory: Path, name: str, content: bytes) -> None:
    (directory / name).write_bytes(content)


def test_measure_counts_gzipped_js_and_css(tmp_path: Path) -> None:
    js = b"console.log('a');" * 100
    css = b"body{color:red}" * 100
    write_asset(tmp_path, "main.js", js)
    write_asset(tmp_path, "main.css", css)
    write_asset(tmp_path, "index.html", b"<html></html>")

    sizes = measure(tmp_path)

    assert sizes["js"] == len(gzip.compress(js, mtime=0))
    assert sizes["css"] == len(gzip.compress(css, mtime=0))
    assert sizes["total"] == sizes["js"] + sizes["css"]


def test_measure_includes_nested_directories(tmp_path: Path) -> None:
    (tmp_path / "static").mkdir()
    write_asset(tmp_path / "static", "chunk.js", b"x" * 1000)

    assert measure(tmp_path)["js"] > 0


def test_same_size_passes() -> None:
    run = {"js": 100_000, "css": 10_000, "total": 110_000}

    assert evaluate(run, run, Limits()) == []


def test_large_growth_fails() -> None:
    base = {"js": 200_000, "css": 10_000, "total": 210_000}
    candidate = {"js": 260_000, "css": 10_000, "total": 270_000}

    failures = evaluate(base, candidate, Limits())

    assert len(failures) == 1
    assert "grew" in failures[0]


def test_small_absolute_growth_passes() -> None:
    # +50% but only 15 KB, under the 20 KB floor.
    base = {"js": 30_000, "css": 0, "total": 30_000}
    candidate = {"js": 45_000, "css": 0, "total": 45_000}

    assert evaluate(base, candidate, Limits()) == []


def test_main_compare_without_baseline_passes(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps({"js": 1, "css": 1, "total": 2}))

    assert main(["compare", str(tmp_path / "missing.json"), str(candidate)]) == 0


def test_main_compare_returns_1_on_growth(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    candidate = tmp_path / "candidate.json"
    base.write_text(json.dumps({"js": 200_000, "css": 0, "total": 200_000}))
    candidate.write_text(json.dumps({"js": 300_000, "css": 0, "total": 300_000}))

    assert main(["compare", str(base), str(candidate)]) == 1


def test_main_measure_writes_json(tmp_path: Path) -> None:
    build = tmp_path / "build"
    build.mkdir()
    write_asset(build, "main.js", b"a" * 500)
    out = tmp_path / "out.json"

    assert main(["measure", str(build), str(out)]) == 0
    assert json.loads(out.read_text())["js"] > 0
