#!/usr/bin/env python3
"""Watch read-only receiver status until an application becomes active."""

from __future__ import annotations

import argparse
import asyncio
import json
import time

from inspect_receiver import inspect


async def watch(
    host: str, port: int, timeout: float, duration: float, interval: float
) -> dict:
    deadline = time.monotonic() + duration
    last_status: dict = {}
    attempts = 0
    while time.monotonic() < deadline:
        attempts += 1
        report = await inspect(
            host, port, timeout, include_availability=False
        )
        last_status = report["receiver_status"]["status"]
        applications = last_status.get("applications") or []
        if applications:
            return {
                "result": "application_active",
                "attempts": attempts,
                "status": last_status,
            }
        await asyncio.sleep(interval)
    return {
        "result": "no_application_seen",
        "attempts": attempts,
        "status": last_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watch Cast receiver status without changing it"
    )
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=8009)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--duration", type=float, default=50.0)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    try:
        report = asyncio.run(
            watch(
                args.host,
                args.port,
                args.timeout,
                args.duration,
                args.interval,
            )
        )
    except (TimeoutError, OSError, RuntimeError) as exc:
        raise SystemExit(f"watch failed: {exc}") from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
