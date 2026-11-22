"""Simulate multiple concurrent clients against the DaaS service and verify responses.

Usage:
    python test_clients.py http://127.0.0.1:5000
    python test_clients.py https://<your-deployed-url> --clients 10 --rounds 5
"""
import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import requests

REQUESTS = [
    ("health check",            "/health",                                       200),
    ("list (default page)",     "/api/courses",                                  200),
    ("search by keyword",       "/api/courses?q=cloud",                          200),
    ("filter by department",    "/api/courses?department=CSE&sort=level",        200),
    ("filter by level+credits", "/api/courses?level=300&min_credits=3",          200),
    ("available seats only",    "/api/courses?available=true&limit=5",           200),
    ("departments summary",     "/api/departments",                              200),
    ("statistics",              "/api/stats",                                    200),
    ("invalid parameter",       "/api/courses?level=abc",                        400),
    ("unknown course",          "/api/courses/XXX000",                           404),
]


def one_client(args):
    client_id, base, rounds = args
    session, out = requests.Session(), []
    for _ in range(rounds):
        for name, path, expected in REQUESTS:
            t0 = time.perf_counter()
            r = session.get(base + path, timeout=30)
            out.append((client_id, name, r.status_code, expected, (time.perf_counter() - t0) * 1000))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("base_url")
    p.add_argument("--clients", type=int, default=5)
    p.add_argument("--rounds", type=int, default=3)
    a = p.parse_args()
    base = a.base_url.rstrip("/")

    # sanity: a known course fetched by code
    first = requests.get(f"{base}/api/courses?limit=1", timeout=30).json()["results"][0]["code"]
    detail = requests.get(f"{base}/api/courses/{first}", timeout=30)
    print(f"Single-record fetch /api/courses/{first}: HTTP {detail.status_code}\n")

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=a.clients) as pool:
        results = [r for chunk in pool.map(one_client, [(i + 1, base, a.rounds) for i in range(a.clients)])
                   for r in chunk]
    wall = time.perf_counter() - t0

    failures = [r for r in results if r[2] != r[3]]
    lat = sorted(r[4] for r in results)
    print(f"Clients: {a.clients}   Rounds: {a.rounds}   Total requests: {len(results)}")
    print(f"Wall time: {wall:.2f}s   Throughput: {len(results) / wall:.1f} req/s")
    print(f"Latency ms  mean={statistics.mean(lat):.1f}  median={statistics.median(lat):.1f}  "
          f"p95={lat[int(len(lat) * 0.95) - 1]:.1f}  max={lat[-1]:.1f}")
    print(f"Unexpected status codes: {len(failures)}")
    for f in failures[:10]:
        print(f"  client {f[0]} '{f[1]}': got {f[2]}, expected {f[3]}")

    print("\nPer-request summary (all clients):")
    print(f"{'request':26} {'status':>7} {'mean ms':>9}")
    for name, _path, expected in REQUESTS:
        rows = [r for r in results if r[1] == name]
        print(f"{name:26} {expected:>7} {statistics.mean(r[4] for r in rows):>9.1f}")
    print("\nRESULT:", "PASS" if not failures else "FAIL")


if __name__ == "__main__":
    main()
