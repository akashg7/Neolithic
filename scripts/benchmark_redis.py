"""Redis HTTP response cache benchmark (bypassed vs cached HIT) against live API.

Measures P50, P95, P99 latency and RPS across read-heavy endpoints using
`Cache-Control: no-cache` (bypassing Redis DB 1 -> hitting PostGIS/ML) vs
warmed Redis cache (`X-FastAPI-Cache: HIT`).

Usage:
    python scripts/benchmark_redis.py --url http://localhost:80 --requests 200 --concurrency 10
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any

import httpx

ENDPOINTS = [
    ("ref_markets", "/api/v1/ref/markets"),
    ("prices_series_180d", "/api/v1/prices/series?commodity_id=cmd_onion&market_id=mkt_lasalgaon&days=180"),
    ("prices_nearby_postgis", "/api/v1/prices/nearby?commodity_id=cmd_onion&district_id=dist_nashik"),
    ("ai_forecast_lgbm", "/api/v1/ai/forecast?commodity=Onion&mandi=Lasalgaon%20APMC"),
    ("market_overview", "/api/v1/market/overview?commodity_id=cmd_onion&market_id=mkt_lasalgaon"),
    ("data_provenance_34k", "/api/v1/meta/data-provenance"),
]


def _pct(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(round(q * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


async def _run_batch(
    client: httpx.AsyncClient,
    path: str,
    *,
    total_requests: int,
    concurrency: int,
    headers: dict[str, str],
) -> dict[str, Any]:
    sem = asyncio.Semaphore(concurrency)
    latencies_ms: list[float] = []
    cache_headers: dict[str, int] = {}
    errors = 0

    async def one_call() -> None:
        nonlocal errors
        async with sem:
            t0 = time.perf_counter()
            try:
                resp = await client.get(path, headers=headers)
                dt = (time.perf_counter() - t0) * 1000.0
                if resp.status_code >= 400:
                    errors += 1
                else:
                    latencies_ms.append(dt)
                    ch = resp.headers.get("X-FastAPI-Cache", "NONE")
                    cache_headers[ch] = cache_headers.get(ch, 0) + 1
            except Exception:
                errors += 1

    t_start = time.perf_counter()
    await asyncio.gather(*(one_call() for _ in range(total_requests)))
    wall_s = max(1e-6, time.perf_counter() - t_start)

    s = sorted(latencies_ms)
    return {
        "requests": total_requests,
        "ok": len(latencies_ms),
        "errors": errors,
        "wall_s": round(wall_s, 3),
        "rps": round(len(latencies_ms) / wall_s, 1),
        "p50_ms": round(statistics.median(s), 2) if s else None,
        "p95_ms": round(_pct(s, 0.95), 2) if s else None,
        "p99_ms": round(_pct(s, 0.99), 2) if s else None,
        "mean_ms": round(statistics.mean(s), 2) if s else None,
        "cache_headers": cache_headers,
    }


async def benchmark(url: str, total_requests: int, concurrency: int) -> dict[str, Any]:
    limits = httpx.Limits(max_connections=max(20, concurrency * 2), max_keepalive_connections=max(20, concurrency))
    results: dict[str, Any] = {}
    async with httpx.AsyncClient(base_url=url.rstrip("/"), timeout=30.0, limits=limits) as client:
        for name, path in ENDPOINTS:
            # Warm once for baseline DB/catalog, then measure uncached (`no-cache`)
            await client.get(path, headers={"Cache-Control": "no-cache"})
            uncached = await _run_batch(
                client,
                path,
                total_requests=total_requests,
                concurrency=concurrency,
                headers={"Cache-Control": "no-cache"},
            )
            # Populate cache once, then measure Redis HITs
            await client.get(path)
            cached = await _run_batch(
                client,
                path,
                total_requests=total_requests,
                concurrency=concurrency,
                headers={},
            )
            p50_speedup = (
                round(uncached["p50_ms"] / cached["p50_ms"], 2)
                if uncached["p50_ms"] and cached["p50_ms"]
                else None
            )
            p95_reduction_pct = (
                round((1.0 - cached["p95_ms"] / uncached["p95_ms"]) * 100.0, 1)
                if uncached["p95_ms"] and cached["p95_ms"]
                else None
            )
            results[name] = {
                "path": path,
                "bypass_cache": uncached,
                "redis_cache": cached,
                "p50_speedup_x": p50_speedup,
                "p95_latency_reduction_pct": p95_reduction_pct,
            }
    return {
        "base_url": url,
        "requests_per_phase": total_requests,
        "concurrency": concurrency,
        "endpoints": results,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:80")
    ap.add_argument("--requests", type=int, default=200)
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    report = asyncio.run(benchmark(args.url, args.requests, args.concurrency))
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
