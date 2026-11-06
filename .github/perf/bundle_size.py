"""Measure the gzipped size of the frontend bundle and compare it with a baseline.

Usage:
  bundle_size.py measure BUILD_DIR OUT.json
  bundle_size.py compare BASELINE.json CANDIDATE.json

The compare step prints a markdown report for the GitHub job summary and exits 1
when the bundle grew past the limits. A missing baseline file passes.
"""

import gzip
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Limits:
    # Fail when the total grows by more than max_ratio AND by more than min_delta.
    max_ratio: float = 1.10
    min_delta: int = 20 * 1024


def measure(build_dir: Path) -> dict[str, int]:
    sizes = {"js": 0, "css": 0}
    for path in sorted(Path(build_dir).rglob("*")):
        kind = path.suffix.lstrip(".")
        if path.is_file() and kind in sizes:
            sizes[kind] += len(gzip.compress(path.read_bytes(), mtime=0))
    return {**sizes, "total": sizes["js"] + sizes["css"]}


def evaluate(base: dict[str, int], candidate: dict[str, int], limits: Limits) -> list[str]:
    delta = candidate["total"] - base["total"]
    if candidate["total"] > base["total"] * limits.max_ratio and delta > limits.min_delta:
        return [
            f"bundle grew from {base['total'] / 1024:.1f} KB to "
            f"{candidate['total'] / 1024:.1f} KB (+{delta / 1024:.1f} KB)"
        ]
    return []


def report(base: dict[str, int] | None, candidate: dict[str, int], failures: list[str]) -> str:
    def kb(run: dict[str, int] | None, key: str) -> str:
        return "n/a" if run is None else f"{run[key] / 1024:.1f}"

    lines = [
        "### Bundle size (gzip, KB)",
        "",
        "| Asset | Baseline | Candidate |",
        "|---|---|---|",
        *(f"| {key} | {kb(base, key)} | {kb(candidate, key)} |" for key in ("js", "css", "total")),
        "",
    ]
    if base is None:
        lines.append("No baseline available; nothing to compare.")
    lines.extend(f"- FAIL: {failure}" for failure in failures)
    if not failures:
        lines.append("Result: no regression.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    command, first, second = argv
    if command == "measure":
        Path(second).write_text(json.dumps(measure(Path(first))))
        return 0

    base_path, candidate_path = Path(first), Path(second)
    base = json.loads(base_path.read_text()) if base_path.exists() else None
    candidate = json.loads(candidate_path.read_text())
    failures = [] if base is None else evaluate(base, candidate, Limits())
    print(report(base, candidate, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
