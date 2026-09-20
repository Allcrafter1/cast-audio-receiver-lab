#!/usr/bin/env python3
"""Read-only Linux process-tree sampling; no commands, URLs or environment exported.

RSS double-counts shared pages; PSS is preferable and may require same-user access.
CPU is measured between samples (100% = one core), not lifetime ps percentages.
Short-lived processes between samples are not observed. No playback is started.
"""
import argparse
import json
import os
from pathlib import Path
import time


def stat_fields(text):
    # comm may contain spaces and parentheses; fields after its final ')' are fixed.
    fields = text[text.rindex(")") + 2:].split()
    return {"ppid": int(fields[1]), "ticks": int(fields[11]) + int(fields[12]),
            "start": int(fields[19]), "rss_kib": int(fields[21]) * os.sysconf("SC_PAGE_SIZE") // 1024}


def snapshot(roots, proc=Path("/proc")):
    records = {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            records[int(entry.name)] = stat_fields((entry / "stat").read_text())
        except (OSError, ValueError, IndexError):
            continue  # normal process exit / inaccessible process
    selected = {pid for pid in roots if pid in records}
    while True:
        children = {pid for pid, record in records.items() if record["ppid"] in selected}
        if children <= selected:
            break
        selected |= children
    result = {}
    for pid in sorted(selected):
        record = records[pid]
        record["pss_kib"] = None
        try:
            for line in (proc / str(pid) / "smaps_rollup").read_text().splitlines():
                if line.startswith("Pss:"):
                    record["pss_kib"] = int(line.split()[1])
        except (OSError, ValueError):
            pass
        result[pid] = record
    return result


def summarize(previous, current, elapsed, ticks_per_second):
    cpu_ticks = sum(max(0, item["ticks"] - previous[pid]["ticks"])
                    for pid, item in current.items()
                    if pid in previous and item["start"] == previous[pid]["start"])
    complete_pss = all(item["pss_kib"] is not None for item in current.values())
    return {"processes": len(current), "rss_kib": sum(item["rss_kib"] for item in current.values()),
            "pss_kib": sum(item["pss_kib"] for item in current.values()) if complete_pss else None,
            "cpu_percent": round(100 * cpu_ticks / ticks_per_second / elapsed, 3),
            "cpu_unmatched_processes": sum(pid not in previous or previous[pid]["start"] != item["start"]
                                           for pid, item in current.items()),
            "exited_processes": sum(pid not in current or current[pid]["start"] != item["start"]
                                    for pid, item in previous.items())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, action="append", required=True,
                        help="explicit root PID; repeat for frontend and manager")
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--interval", type=float, default=1)
    args = parser.parse_args()
    if (any(pid <= 1 for pid in args.pid) or not 1 <= args.samples <= 3600
            or not .1 <= args.interval <= 60):
        parser.error("PID must exceed 1; samples 1..3600; interval 0.1..60 seconds")
    previous = snapshot(args.pid)
    identities = {pid: previous[pid]["start"] for pid in args.pid if pid in previous}
    if len(identities) != len(set(args.pid)):
        parser.error("one or more selected root processes are unavailable")
    last = time.monotonic()
    ticks = os.sysconf("SC_CLK_TCK")
    for index in range(args.samples):
        time.sleep(args.interval)
        current = snapshot(args.pid)
        now = time.monotonic()
        if any(pid not in current or current[pid]["start"] != start for pid, start in identities.items()):
            print(json.dumps({"stopped": "selected_root_exited_or_replaced"}), flush=True)
            return
        print(json.dumps(dict(sample=index + 1, elapsed_seconds=round(now-last, 3),
                              **summarize(previous, current, now-last, ticks))), flush=True)
        previous, last = current, now


if __name__ == "__main__":
    main()
