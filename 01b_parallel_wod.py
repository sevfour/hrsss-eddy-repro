"""Finish the WOD download in parallel.

The serial 01_download_wod.py fetches one file at a time. This version fetches
several concurrently (NCEI serves many streams fine), skipping files already
complete on disk and resuming partial ones with curl -C -. Idempotent: re-run
any time to fill whatever is missing.
"""
import sys
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

WORKERS = 6


def remote_size(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            return int(r.headers.get("Content-Length", 0))
    except Exception:
        return None


def fetch(year, plat):
    fname = f"wod_{plat}_{year}.nc"
    url = f"{C.WOD_BASE}/{year}/{fname}"
    dest = C.WOD_DIR / fname
    exp = remote_size(url)
    if exp is None:
        return fname, "absent"
    if dest.exists() and dest.stat().st_size == exp:
        return fname, "have"
    # resumable, retrying, abort-if-stalled
    for attempt in range(6):
        subprocess.run(
            ["curl", "-sS", "-C", "-", "--connect-timeout", "30",
             "--speed-limit", "50000", "--speed-time", "120",
             "-o", str(dest), url],
        )
        if dest.exists() and dest.stat().st_size == exp:
            return fname, f"done ({exp/1e6:.0f}MB)"
    return fname, "INCOMPLETE"


def main():
    tasks = [(y, p) for y in C.YEARS for p in C.PLATFORMS]
    # quick pre-filter of obviously-complete files to cut HEAD calls
    todo = []
    for y, p in tasks:
        f = C.WOD_DIR / f"wod_{p}_{y}.nc"
        todo.append((y, p))
    print(f"checking/fetching {len(todo)} files with {WORKERS} workers", flush=True)
    done = have = absent = bad = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, y, p): (y, p) for y, p in todo}
        for fut in as_completed(futs):
            fname, status = fut.result()
            if status.startswith("done"):
                done += 1
                print(f"  {status:16s} {fname}", flush=True)
            elif status == "have":
                have += 1
            elif status == "absent":
                absent += 1
            else:
                bad += 1
                print(f"  {status:16s} {fname}", flush=True)
    print(f"\nsummary: {done} downloaded, {have} already had, "
          f"{absent} not-on-server, {bad} incomplete", flush=True)


if __name__ == "__main__":
    main()
