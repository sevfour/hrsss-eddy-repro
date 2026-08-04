"""Chunked, parallel, resumable downloader for the AVISO eddy files.

The AVISO gateway throttles sustained single connections to ~10 KB/s, but
serves short byte-range requests at full speed before the throttle engages.
So we split each file into fixed-size chunks, fetch many chunks concurrently
with short-lived curl range requests, and retry until every chunk is present.
Fully resumable: completed chunks are cached on disk and skipped on re-run.
"""
import sys
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

AVISO_GW = ("https://data.aviso.altimetry.fr/aviso-gateway/data/"
            "META3.1exp_DT/META3.1exp_DT_allsat")
FILES = [
    "META3.1exp_DT_allsat_Anticyclonic_long_19930101_20200307.nc",
    "META3.1exp_DT_allsat_Cyclonic_long_19930101_20200307.nc",
]

CHUNK = 8 * 1024 * 1024      # 8 MB chunks (short enough to dodge the throttle)
WORKERS = 8                  # parallel range requests
MAX_PASSES = 100             # re-scan passes to fill remaining gaps


def remote_size(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def fetch_chunk(url, idx, start, end, parts_dir):
    """Download byte range [start, end] to parts_dir/<idx>.part unless already
    the right size. Returns (idx, ok)."""
    part = parts_dir / f"{idx:06d}.part"
    want = end - start + 1
    if part.exists() and part.stat().st_size == want:
        return idx, True
    r = subprocess.run(
        ["curl", "-sS", "-r", f"{start}-{end}",
         "--connect-timeout", "30", "--max-time", "120",
         "-o", str(part), url],
    )
    ok = r.returncode == 0 and part.exists() and part.stat().st_size == want
    if not ok and part.exists():
        part.unlink()  # drop bad/short chunk so it retries next pass
    return idx, ok


def assemble(parts_dir, dest, n_chunks):
    with open(dest, "wb") as out:
        for i in range(n_chunks):
            part = parts_dir / f"{i:06d}.part"
            with open(part, "rb") as p:
                out.write(p.read())


def download_file(fname):
    url = f"{AVISO_GW}/{fname}"
    dest = C.EDDY_DIR / fname
    size = remote_size(url)
    if dest.exists() and dest.stat().st_size == size:
        print(f"{fname}: already complete ({size/1e9:.2f} GB)", flush=True)
        return True
    parts_dir = C.EDDY_DIR / (fname + ".parts")
    parts_dir.mkdir(exist_ok=True)
    ranges = []
    idx = 0
    for start in range(0, size, CHUNK):
        end = min(start + CHUNK - 1, size - 1)
        ranges.append((idx, start, end))
        idx += 1
    n_chunks = len(ranges)
    print(f"{fname}: {size/1e9:.2f} GB in {n_chunks} chunks", flush=True)

    for p in range(1, MAX_PASSES + 1):
        todo = [(i, s, e) for (i, s, e) in ranges
                if not (parts_dir / f"{i:06d}.part").exists()
                or (parts_dir / f"{i:06d}.part").stat().st_size != (e - s + 1)]
        if not todo:
            break
        done_now = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = [ex.submit(fetch_chunk, url, i, s, e, parts_dir)
                    for (i, s, e) in todo]
            for fut in as_completed(futs):
                _, ok = fut.result()
                if ok:
                    done_now += 1
        have = n_chunks - len(todo) + done_now
        print(f"  pass {p}: {have}/{n_chunks} chunks "
              f"({have*CHUNK/1e9:.2f} GB)", flush=True)

    remaining = [i for (i, s, e) in ranges
                 if not (parts_dir / f"{i:06d}.part").exists()]
    if remaining:
        print(f"  INCOMPLETE: {len(remaining)} chunks missing", flush=True)
        return False
    print(f"  assembling -> {dest.name}", flush=True)
    assemble(parts_dir, dest, n_chunks)
    if dest.stat().st_size == size:
        # clean up chunk cache
        for pp in parts_dir.glob("*.part"):
            pp.unlink()
        parts_dir.rmdir()
        print(f"  DONE {fname} ({size/1e9:.2f} GB)", flush=True)
        return True
    print(f"  assembled size mismatch!", flush=True)
    return False


def main():
    ok = True
    for f in FILES:
        if not download_file(f):
            ok = False
    print("ALL COMPLETE" if ok else "SOME INCOMPLETE — re-run to resume", flush=True)


if __name__ == "__main__":
    main()
