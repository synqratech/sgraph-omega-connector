from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(summary: dict[str, Any], name: str) -> dict[str, Any]:
    metrics = summary.get("metrics", {})
    raw = metrics.get(name, {})
    return raw if isinstance(raw, dict) else {}


def _values(summary: dict[str, Any], name: str) -> dict[str, Any]:
    metric = _metric(summary, name)
    data = metric.get("values", {})
    if isinstance(data, dict) and data:
        return data
    return metric


def _extract(summary: dict[str, Any]) -> dict[str, Any]:
    duration = _values(summary, "http_req_duration")
    failed = _values(summary, "http_req_failed")
    fallback = _values(summary, "fallback_rate")
    unexpected_fallback = _values(summary, "unexpected_fallback_rate")
    scenario_error = _values(summary, "scenario_error_rate")
    p50 = duration.get("p(50)")
    if p50 is None:
        p50 = duration.get("med", 0.0)
    p95 = duration.get("p(95)")
    if p95 is None:
        p95 = duration.get("p95", 0.0)
    p99 = duration.get("p(99)")
    if p99 is None:
        p99 = duration.get("p99", 0.0)
    err_value = failed.get("rate")
    if err_value is None:
        err_value = failed.get("value", 0.0)
    fallback_value = fallback.get("rate")
    if fallback_value is None:
        fallback_value = fallback.get("value", 0.0)
    unexpected_fallback_value = unexpected_fallback.get("rate")
    if unexpected_fallback_value is None:
        unexpected_fallback_value = unexpected_fallback.get("value", 0.0)
    scenario_error_value = scenario_error.get("rate")
    if scenario_error_value is None:
        scenario_error_value = scenario_error.get("value", 0.0)
    return {
        "http_req_failed_rate": float(err_value),
        "fallback_rate": float(fallback_value),
        "unexpected_fallback_rate": float(unexpected_fallback_value),
        "scenario_error_rate": float(scenario_error_value),
        "latency_ms": {
            "p50": float(p50 or 0.0),
            "p95": float(p95 or 0.0),
            "p99": float(p99 or 0.0),
            "avg": float(duration.get("avg", 0.0)),
        },
    }


def _markdown(data: dict[str, Any]) -> str:
    baseline = data.get("baseline", {})
    stress = data.get("stress", {})
    b_lat = baseline.get("latency_ms", {})
    s_lat = stress.get("latency_ms", {})
    return "\n".join(
        [
            "# Performance Report",
            "",
            "| Profile | Error rate | Fallback rate | p50 ms | p95 ms | p99 ms |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            (
                f"| baseline | {baseline.get('http_req_failed_rate', 0.0):.4f} | "
                f"{baseline.get('fallback_rate', 0.0):.4f} "
                f"(unexpected {baseline.get('unexpected_fallback_rate', 0.0):.4f}) | "
                f"{b_lat.get('p50', 0.0):.1f} | {b_lat.get('p95', 0.0):.1f} | {b_lat.get('p99', 0.0):.1f} |"
            ),
            (
                f"| stress | {stress.get('http_req_failed_rate', 0.0):.4f} | "
                f"{stress.get('fallback_rate', 0.0):.4f} | "
                f"{s_lat.get('p50', 0.0):.1f} | {s_lat.get('p95', 0.0):.1f} | {s_lat.get('p99', 0.0):.1f} |"
            ),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build markdown/json report from k6 summaries")
    parser.add_argument("--baseline", default="artifacts/perf/baseline-summary.json")
    parser.add_argument("--stress", default="artifacts/perf/stress-summary.json")
    parser.add_argument("--out-json", default="artifacts/perf/perf-report.json")
    parser.add_argument("--out-md", default="artifacts/perf/perf-report.md")
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    stress_path = Path(args.stress)
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)

    if not baseline_path.exists() or not stress_path.exists():
        missing = [str(p) for p in [baseline_path, stress_path] if not p.exists()]
        raise SystemExit(f"missing k6 summary files: {', '.join(missing)}")

    result = {
        "baseline": _extract(_load(baseline_path)),
        "stress": _extract(_load(stress_path)),
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_markdown(result), encoding="utf-8")
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
